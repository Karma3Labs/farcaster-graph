"""
Token distribution tasks for Airflow DAG with proper parallelization and idempotency.

This module implements the new task-based architecture for token distribution:
1. ``gather_rounds_due()`` - Identify rounds to process
2. ``fetch_leaderboard()`` - Fetch leaderboard data per round
3. ``calculate()`` - Calculate and atomically insert distribution logs
4. ``verify()`` - Verify calculations against budget
5. ``submit_txs()`` - Submit blockchain transactions with nonce management
6. ``wait_for_confirmations()`` - Wait for blockchain confirmations
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone

import aiohttp
import asyncpg
import chain_index
import niquests
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address, to_hex
from hexbytes import HexBytes
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from urllib3.util import Retry
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.middleware import SignAndSendRawMiddlewareBuilder

import cura_utils
from config import settings
from db_utils import get_supabase_psycopg2_client
from k3l.fcgraph.pipeline.db_utils import psycopg2_cursor, psycopg2_query
from k3l.fcgraph.pipeline.models import (
    UUID,
    BigInt,
    EthAddress,
    TxHash,
    api_context,
)
from k3l.fcgraph.pipeline.token_distribution.leaderboard import LeaderboardRow
from k3l.fcgraph.pipeline.token_distribution.models import (
    Log,
    Request,
    Round,
    RoundMethod,
)

logger = logging.getLogger(__name__)


def rpc_for_chain_id(chain_id: int):
    try:
        return settings.ETH_RPC_URLS[chain_id]
    except KeyError:
        pass
    # noinspection PyTypeHints
    return chain_index.get_chain_info(chain_id).rpc[0]


ERC20_ABI = json.loads("""
[
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "name": "",
                "type": "string"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_spender",
                "type": "address"
            },
            {
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "approve",
        "outputs": [
            {
                "name": "",
                "type": "bool"
            }
        ],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_from",
                "type": "address"
            },
            {
                "name": "_to",
                "type": "address"
            },
            {
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "transferFrom",
        "outputs": [
            {
                "name": "",
                "type": "bool"
            }
        ],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "name": "",
                "type": "uint8"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [
            {
                "name": "_owner",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "name": "balance",
                "type": "uint256"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "name": "",
                "type": "string"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_to",
                "type": "address"
            },
            {
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "transfer",
        "outputs": [
            {
                "name": "",
                "type": "bool"
            }
        ],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [
            {
                "name": "_owner",
                "type": "address"
            },
            {
                "name": "_spender",
                "type": "address"
            }
        ],
        "name": "allowance",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "payable": true,
        "stateMutability": "payable",
        "type": "fallback"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": true,
                "name": "spender",
                "type": "address"
            },
            {
                "indexed": false,
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Approval",
        "type": "event"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "name": "from",
                "type": "address"
            },
            {
                "indexed": true,
                "name": "to",
                "type": "address"
            },
            {
                "indexed": false,
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Transfer",
        "type": "event"
    }
]
""")


def fix_double_encoded_address(
    address_bytes: bytes | memoryview | None,
) -> ChecksumAddress | None:
    """
    Fix Neynar's buggy double-encoded addresses.

    Sometimes Neynar stores ASCII bytes of the hex string instead of raw bytes.
    E.g., instead of ``b'\\x00\\x00...'`` they store ``b'0x0000...'`` as ASCII.

    :param address_bytes: Raw bytes/memoryview from the database (could be double-encoded)
    :returns: Valid checksum address or None if invalid
    """
    if not address_bytes:
        return None

    # First, try normal conversion (for correctly stored addresses)
    try:
        return to_checksum_address(address_bytes)
    except (TypeError, ValueError):
        pass

    # If that fails, check if it's double-encoded ASCII
    if isinstance(address_bytes, memoryview):
        address_bytes = address_bytes.tobytes()

    try:
        address_str = address_bytes.decode("ascii")
    except UnicodeDecodeError:  # Expected for non-ASCII bytes
        pass
    else:
        # Decoding succeeded, check if it's a hex-encoded address
        address_without_0x = address_str.lower().removeprefix("0x")
        if len(address_without_0x) == 40 and all(
            c in "0123456789abcdef" for c in address_without_0x
        ):
            # This is double-encoded, convert the string to address
            return to_checksum_address("0x" + address_without_0x)
        # Decoding succeeded, but it's not a hex address - continue to other cases

    # Out of all options
    logger.warning(f"Could not parse address from database: {address_bytes!r}")
    return None


def validate_funding(round_id: UUID, amount: int) -> bool:
    """
    Validate that the distribution round is fully funded.

    Checks that: total_funded >= (already_scheduled + current_round_amount)

    :param round_id: UUID string of the round to validate
    :param amount: Amount to distribute in the current round
    :returns: True if sufficient funding exists, False otherwise
    """
    query = """
    WITH current_round_info AS (
        SELECT request_id, scheduled
        FROM token_distribution.rounds
        WHERE id = %(round_id)s
    ),
    total_funded AS (
        SELECT COALESCE(SUM(ft.amount), 0) as funded
        FROM token_distribution.funding_txs ft
        WHERE ft.request_id = (SELECT request_id FROM current_round_info)
    ),
    already_scheduled AS (
        SELECT COALESCE(SUM(r.amount), 0) as scheduled
        FROM token_distribution.rounds r
        WHERE r.request_id = (SELECT request_id FROM current_round_info)
          AND r.scheduled < (SELECT scheduled FROM current_round_info)  -- Past rounds only
    )
    SELECT funded, scheduled
    FROM total_funded, already_scheduled
    """

    class Args(BaseModel):
        round_id: UUID

    class Row(BaseModel):
        funded: BigInt
        scheduled: BigInt

    with get_supabase_psycopg2_client() as conn, psycopg2_cursor(conn) as cur:
        for result in psycopg2_query(cur, query, Args(round_id=round_id), Row):
            break
        else:
            raise RuntimeError(f"Could not fetch funding info for round {round_id}")

    funded = result.funded
    scheduled = result.scheduled
    available = funded - scheduled
    requested = amount

    logger.info(
        f"Funding check for round {round_id}: "
        f"funded={funded}, already_scheduled={scheduled}, "
        f"available={available}, requested={requested}"
    )

    if available < requested:
        logger.info(
            f"Insufficient funding for round {round_id}: "
            f"available={available} < requested={requested} "
            f"(total_funded={funded}, already_scheduled={scheduled}). "
            f"Skipping distribution until funding is complete."
        )
        return False

    return True


def get_last_successful_round_timestamp(round_id: UUID) -> datetime:
    """
    Get the timestamp of the last successfully processed round before the given round.

    :param round_id: UUID string of the current round
    :returns: Datetime of the last successful round, or epoch (2000-01-01) if none exists
    """
    query = """
    WITH current_round AS (
        SELECT request_id, scheduled
        FROM token_distribution.rounds
        WHERE id = %s
    )
    SELECT MAX(r.scheduled) as last_scheduled
    FROM token_distribution.rounds r
    JOIN token_distribution.logs l ON r.id = l.round_id
    WHERE r.request_id = (SELECT request_id FROM current_round)
      AND r.scheduled < (SELECT scheduled FROM current_round)
      AND l.tx_hash IS NOT NULL  -- Only consider rounds with submitted transactions
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (round_id,))
            result = cur.fetchone()
            last_timestamp = (
                result[0]
                if result and result[0]
                else datetime(2000, 1, 1, tzinfo=timezone.utc)
            )
            logger.info(
                f"Last successful round timestamp for {round_id}: {last_timestamp}"
            )
            return last_timestamp


def gather_rounds_due(cutoff: datetime) -> list[Round]:
    """
    Gather all rounds that are due for processing as of the execution date.

    :param cutoff: Datetime object representing the DAG execution date
    :returns: List of round UUID strings that need processing
    """
    query = """
    SELECT r.*
    FROM token_distribution.rounds r
    LEFT JOIN token_distribution.logs l ON r.id = l.round_id
    WHERE r.scheduled <= %(cutoff)s
      AND l.id IS NULL  -- No logs exist yet
    GROUP BY r.id, r.scheduled
    ORDER BY r.scheduled
    """

    class Args(BaseModel):
        cutoff: datetime

    with get_supabase_psycopg2_client() as conn, psycopg2_cursor(conn) as cur:
        rounds = list(psycopg2_query(cur, query, Args(cutoff=cutoff), Round))
        logger.info(f"Found {len(rounds)} rounds due for processing as of {cutoff}")
        return rounds


class RoundData(BaseModel):
    round: Round
    request: Request
    leaderboard: list[LeaderboardRow]
    start_time: datetime
    end_time: datetime


async def collect_round_data_async(round_: Round) -> RoundData:
    """
    Async function to fetch leaderboard data for a specific round.

    :param round_: The round row.
    :returns: Round and leaderboard data.
    """
    query = """
    SELECT *
    FROM token_distribution.requests req
    WHERE id = %(id)s
    """

    class Args(BaseModel):
        id: UUID

    with get_supabase_psycopg2_client() as conn, psycopg2_cursor(conn) as cur:
        for req in psycopg2_query(cur, query, Args(id=round_.request_id), Request):
            break
        else:
            msg = f"Request {round_.request_id} for round {round_.id} not found"
            raise ValueError(msg)

    # Convert the token address to ChecksumAddress (handles bytes/memoryview/str)
    # Get time window for leaderboard
    # Start time is the last successful round timestamp or epoch
    start_time = get_last_successful_round_timestamp(round_.id)
    # End time is the current round's scheduled time
    end_time = round_.scheduled

    # Fetch leaderboard from API
    url = f"{settings.FCGRAPH_API_URL}/tokens/{req.recipient_token_community}/leaderboards/trader"

    # If no limit, fetch a large number (API default or max)
    limit = round_.num_recipients
    limit = req.num_recipients_per_round if limit is None else limit
    actual_limit = limit if limit > 0 else 10000

    # Include time window parameters
    logger.info(
        f"Fetching leaderboard for token {req.recipient_token_community} "
        f"from {start_time} to {end_time}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            params={
                "limit": actual_limit,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        ) as response:
            response.raise_for_status()
            leaderboard_data = await response.json()

            # Apply limit if specified and not unlimited
            if 0 < limit < len(leaderboard_data["result"]):
                leaderboard_data["result"] = leaderboard_data["result"][:limit]

    leaderboard = [
        LeaderboardRow.model_validate(row, context=api_context)
        for row in leaderboard_data["result"]
    ]
    method = round_.method or req.round_method
    logger.info(
        f"Fetched {len(leaderboard_data['result'])} entries for round {round_.id}, "
        f"method: {method}, limit: {limit if limit > 0 else 'unlimited'}, "
        f"time window: {start_time} to {end_time}"
    )
    logger.debug(f"Leaderboard: {leaderboard}")

    return RoundData(
        round=round_,
        request=req,
        leaderboard=leaderboard,
        start_time=start_time,
        end_time=end_time,
    )


def collect_round_data(round_: Round) -> RoundData:
    """
    Synchronous wrapper for fetch_leaderboard_async.

    :param round_: The round to fetch.
    :returns: Round data.
    """
    return asyncio.run(collect_round_data_async(round_))


async def get_wallet_addresses_async(
    fids: list[int],
) -> dict[int, ChecksumAddress | None]:
    """
    Fetch primary wallet addresses for FIDs from neynarv3.profiles.

    :param fids: List of Farcaster IDs
    :returns: Dictionary mapping FID to ChecksumAddress
    """
    query = """
    SELECT fid, primary_eth_address
    FROM neynarv3.profiles
    WHERE fid = ANY($1::int[])
    """

    # Create a connection to eigen8
    # noinspection PyUnresolvedReferences
    # (asyncpg.create_pool() returns a Pool object, which actually is an awaitable.)
    pool = await asyncpg.create_pool(
        host=settings.ALT_DB_HOST,
        port=settings.ALT_DB_PORT,
        user=settings.ALT_DB_USER,
        password=settings.ALT_DB_PASSWORD.get_secret_value(),
        database=settings.ALT_DB_NAME,
        min_size=1,
        max_size=10,
    )

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, fids)
            # Convert bytea to ChecksumAddress at the database boundary, handling Neynar's double-encoding bug
            return {
                row["fid"]: fix_double_encoded_address(row["primary_eth_address"])
                for row in rows
            }
    finally:
        await pool.close()


class Distribution(BaseModel):
    fid: int
    wallet_address: ChecksumAddress | None
    amount: int
    points: int


class RoundLogs(BaseModel):
    round_data: RoundData
    logs: list[Log]


def calculate(rd: RoundData) -> list[Log]:
    """
    Calculate distribution amounts and atomically insert into the logs.

    :param rd: Round data, with round_id, amount, method, and leaderboard
    :returns: List of logs
    """
    round_id = rd.round.id
    amount = rd.round.amount
    method = rd.round.method or rd.request.round_method
    leaderboard = rd.leaderboard
    # Validate funding before proceeding
    if not validate_funding(round_id, amount):
        logger.info(f"Skipping round {round_id} due to insufficient funding")
        return []

    # Get wallet addresses for all FIDs
    fids = [entry.fid for entry in leaderboard]
    wallet_addresses = asyncio.run(get_wallet_addresses_async(fids))

    # Calculate distributions based on the method

    distributions: list[Distribution] = []

    # Process all entries, including those without wallet addresses
    if not leaderboard:
        logger.warning(f"No recipients for round {round_id}")
        return []

    weights: dict[int, int] = {}
    match method:
        case RoundMethod.UNIFORM:
            weights.update((entry.fid, 1) for entry in leaderboard)
        case RoundMethod.PROPORTIONAL:
            weights.update((entry.fid, entry.score) for entry in leaderboard)
        case _:
            raise ValueError(f"Unknown distribution method: {method}")

    total_weight = sum(weight for (fid, weight) in weights.items())
    if total_weight == 0:
        logger.warning(f"Total weight is 0 for round {round_id}, cannot distribute")
        return []

    cumulative_weight = 0
    cumulative_amount = 0
    for entry in leaderboard:
        cumulative_weight += weights[entry.fid]
        dist_amount = amount * cumulative_weight // total_weight - cumulative_amount
        cumulative_amount += dist_amount

        wallet_address = wallet_addresses.get(entry.fid)
        distributions.append(
            Distribution(
                fid=entry.fid,
                wallet_address=wallet_address,
                amount=dist_amount,
                points=entry.score,
            )
        )

    assert cumulative_weight == total_weight
    assert cumulative_amount == amount

    # Insert all logs atomically
    logs: list[Log] = []

    class InsertArgs(BaseModel):
        round_id: UUID
        receiver: EthAddress | None
        amount: int
        fid: int
        points: int

    with get_supabase_psycopg2_client() as conn:
        conn.autocommit = False
        with psycopg2_cursor(conn) as cur:
            try:
                for dist in distributions:
                    logs.extend(
                        psycopg2_query(
                            cur,
                            """
                            INSERT INTO token_distribution.logs (round_id, receiver, amount, fid, points)
                            VALUES (%(round_id)s, %(receiver)s, %(amount)s, %(fid)s, %(points)s)
                            RETURNING *
                            """,
                            InsertArgs(
                                round_id=round_id,
                                receiver=dist.wallet_address,
                                amount=dist.amount,
                                fid=dist.fid,
                                points=dist.points,
                            ),
                            Log,
                        )
                    )

            except Exception as e:
                conn.rollback()
                logger.error(
                    f"Failed to insert logs for round {round_id}: {e}", exc_info=True
                )
                raise

            else:
                conn.commit()
                logger.info(
                    f"Created {len(logs)} distribution logs for round {round_id} "
                    f"using {method} method"
                )

    return logs


def verify(logs: list[Log], round_data: RoundData) -> list[Log]:
    """
    Verify that calculated distributions match the round budget.

    :param logs: Logs to verify.
    :param round_data: Round data.
    :returns: The given logs (pass-through for the next task).
    :raises ValueError: If the calculated amount doesn't match the expected amount.
    """

    # Sum up calculated logs
    actual_amount = sum(log.amount for log in logs)

    difference = abs(round_data.round.amount - actual_amount)
    if difference != 0:
        error_msg = (
            f"Amount mismatch for round {round_data.round.id}: "
            f"expected {round_data.round.amount}, calculated {actual_amount}, "
            f"difference {difference}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"Verification passed for round {round_data.round.id}: "
        f"{actual_amount} tokens to {len(logs)} recipients"
    )

    return logs


def submit_txs(rounds: list[RoundLogs]) -> list[RoundLogs]:
    """
    Submit blockchain transactions for all verified distributions.

    This task handles all transactions serially to manage nonce properly.

    :param rounds: Verified rounds' data and logs.
    :returns: Same `rounds` with TX hashes populated in the log.
    """

    with get_supabase_psycopg2_client() as conn:
        conn.autocommit = False
        with psycopg2_cursor(conn) as cur:
            for rl in rounds:
                req = rl.round_data.request
                round_ = rl.round_data.round
                logger.info(f"Processing round {round_.id}")

                chain_id = rl.round_data.request.chain_id
                # Initialize Web3
                w3 = Web3(Web3.HTTPProvider(rpc_for_chain_id(chain_id)))
                account = w3.eth.account.from_key(
                    settings.CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY.get_secret_value()
                )
                sign_and_send_raw_middleware = SignAndSendRawMiddlewareBuilder.build(
                    account
                )
                w3.middleware_onion.inject(sign_and_send_raw_middleware, layer=0)
                w3.eth.default_account = account.address
                contract = w3.eth.contract(address=req.token_address, abi=ERC20_ABI)

                # Get current nonce
                nonce = w3.eth.get_transaction_count(account.address, "pending")

                try:
                    for log in rl.logs:
                        assert log.tx_hash is None, f"{log=} already has tx hash"
                        logger.debug(f"Processing log {log.id}")
                        # Build ERC20 transfer transaction
                        # This assumes token_address is an ERC20 token
                        # Would need to handle native token transfers differently

                        # Convert receiver bytes and token bytes to ChecksumAddress
                        receiver_address = log.receiver
                        if receiver_address is None:
                            logger.info(f"distribution {log} has no receiver, skipping")
                            continue
                        # Build transfer data using "transfer(address to, uint256 amount)"
                        tx_hash: HexBytes = contract.functions.transfer(
                            receiver_address, log.amount
                        ).transact({"chainId": chain_id, "nonce": nonce, "gas": 100000})

                        # Update the log with tx hash (store as bytes in the database)
                        class UpdateArgs(BaseModel):
                            id: UUID
                            tx_hash: TxHash

                        logger.debug(f"Submitted tx {to_hex(tx_hash)} for log {log.id}")

                        updated_logs = psycopg2_query(
                            cur,
                            """
                            UPDATE token_distribution.logs
                            SET tx_hash = %(tx_hash)s
                            WHERE id = %(id)s
                            RETURNING *
                            """,
                            UpdateArgs(id=log.id, tx_hash=to_hex(tx_hash)),
                            Log,
                        )
                        for _ in updated_logs:
                            break
                        else:
                            raise ValueError(f"Log {log.id} not updated")

                        log.tx_hash = to_hex(tx_hash)
                        nonce += 1

                except Exception as e:
                    conn.rollback()
                    logger.error(
                        f"Failed to submit transactions for logs: {e}", exc_info=True
                    )
                    raise
                else:
                    conn.commit()

    return rounds


def wait_for_confirmations(round_logs: list[RoundLogs]) -> list[Log]:
    """Wait for all transaction confirmations on the blockchain.

    :param round_logs: Round + logs data
    :return: The confirmed logs.
    :raises ValueError: If any transaction is reverted.
    :raises TimeoutError: If the transaction is not confirmed within timeout.
    """

    confirmed_logs: list[Log] = []
    for rl in round_logs:
        chain_id = rl.round_data.request.chain_id
        w3 = Web3(Web3.HTTPProvider(rpc_for_chain_id(chain_id)))
        for log in rl.logs:
            tx_hash = log.tx_hash
            if tx_hash is None:
                continue
            retries = 0
            max_retries = 120  # 10 minutes with 5-second intervals

            while retries < max_retries:
                try:
                    receipt = w3.eth.get_transaction_receipt(tx_hash)
                    if receipt["status"] == 1:
                        logger.info(
                            f"TX {tx_hash} confirmed in block {receipt['blockNumber']}"
                        )
                        break
                    else:
                        raise ValueError(
                            f"Transaction {tx_hash} was reverted! {receipt=}"
                        )
                except TransactionNotFound:
                    retries += 1
                    time.sleep(5)

            if retries >= max_retries:
                raise TimeoutError(
                    f"Transaction {tx_hash} not confirmed after {max_retries * 5} seconds"
                )
            confirmed_logs.append(log)

    logger.info("All transactions confirmed successfully")
    return confirmed_logs


def notify_recipients(logs: list[Log]) -> None:
    """Send notifications to all recipients who received rewards.

    Notification message format:
    - With token_symbol: "Your trades & casts for {TOKEN} paid off. You've earned
      an airdrop from the Believer Leaderboard. Check rank"
    - Without token_symbol: "Your trades & casts paid off. You've earned an airdrop
      from the Believer Leaderboard. Check rank"

    Target URL: ``https://cura.network/{token_address}/leaderboard?category=believers``

    :param logs: Confirmed logs.
    """
    # Flatten nested lists
    all_log_ids = [log.id for log in logs]

    if not all_log_ids:
        logger.info("No logs to send notifications for")
        return

    logger.info(f"Sending notifications for {len(all_log_ids)} distribution logs")

    # Query database to get FIDs and metadata grouped by round and token
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    l.round_id,
                    req.token_address,
                    ARRAY_AGG(l.fid) as fids,
                    r.metadata as round_metadata,
                    req.metadata as request_metadata
                FROM token_distribution.logs l
                JOIN token_distribution.rounds r ON l.round_id = r.id
                JOIN token_distribution.requests req ON r.request_id = req.id
                WHERE l.id = ANY(%s::uuid[])
                GROUP BY l.round_id, req.token_address, r.metadata, req.metadata
                """,
                (all_log_ids,),
            )

            rounds_data = cur.fetchall()

    if not rounds_data:
        logger.warning("No round data found")
        return

    # Set up an HTTP session for notifications
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"POST"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0

    with niquests.Session(retries=retries) as session:
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)

        # Process each round
        for round_data in rounds_data:
            round_id = round_data["round_id"]
            fids = round_data["fids"]

            # Convert token_address from bytea to ChecksumAddress
            token_address_raw = round_data["token_address"]
            token_address = fix_double_encoded_address(token_address_raw)

            if not token_address:
                logger.error(
                    f"Could not convert token_address for round {round_id}, skipping notifications"
                )
                continue

            # Extract token_symbol from metadata
            # Check round_metadata first, then request_metadata
            token_symbol = None

            if round_data["round_metadata"]:
                token_symbol = round_data["round_metadata"].get("token_symbol")

            if not token_symbol and round_data["request_metadata"]:
                token_details = round_data["request_metadata"].get("token") or {}
                token_symbol = token_details.get("symbol")

            # Generate notification message
            title = "Believer Leaderboard earnings"

            if token_symbol:
                body = f"Your trades and casts for {token_symbol} paid off. Check rank on the believer leaderboard."
            else:
                body = "Your trades and casts paid off. Check rank on the believer leaderboard."
                logger.info(
                    f"No token_symbol found in metadata for round {round_id}, using generic message"
                )

            # Generate unique notification_id using round_id and token_address
            notification_id = hashlib.sha256(
                f"token-distribution-{round_id}-{token_address}".encode("utf-8")
            ).hexdigest()

            # Generate target URL with the token address
            target_url = (
                f"https://cura.network/{token_address}/leaderboard?category=believers"
            )

            logger.info(
                f"Sending notifications for round {round_id} to {len(fids)} recipients "
                f"token={token_symbol or 'N/A'}, address={token_address})"
            )

            cura_utils.notify(
                session=session,
                timeouts=timeouts,
                channel_id="",
                fids=fids,
                notification_id=notification_id,
                title=title,
                body=body,
                target_url=target_url,
            )

    logger.info(
        f"Successfully sent notifications for {len(rounds_data)} rounds "
        f"covering {len(all_log_ids)} recipients"
    )

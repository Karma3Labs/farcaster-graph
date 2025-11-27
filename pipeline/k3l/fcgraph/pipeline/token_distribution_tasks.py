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
from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal

import aiohttp
import asyncpg
import chain_index
import niquests
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address, to_hex
from hexbytes import HexBytes
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
    JSON,
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
from k3l.fcgraph.pipeline.utils import ticks_until_timeout

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
    WHERE r.scheduled <= %(cutoff)s
      AND r.fulfilled_at IS NULL
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


def collect_round_data(round_: Round) -> UUID:
    """
    Fetch leaderboard and insert into the `logs` table atomically.

    This declares "these and only these people will be rewarded for this round"
    by inserting log entries with round_id, fid, and points. The receiver and
    amount fields are populated later by calculate().

    :param round_: The round to fetch.
    :returns: Round ID.
    """
    round_data = asyncio.run(collect_round_data_async(round_))
    round_id = round_data.round.id

    class InsertArgs(BaseModel):
        round_id: UUID
        fid: int
        points: int

    # Insert leaderboard entries into logs atomically
    with (
        get_supabase_psycopg2_client() as conn,
        psycopg2_cursor(conn, commit="on_success") as cur,
    ):

        class RoundArg(BaseModel):
            round_id: UUID

        class RoundResult(BaseModel):
            recipients_selected_at: datetime | None

        result = list(
            psycopg2_query(
                cur,
                """
                SELECT recipients_selected_at
                FROM token_distribution.rounds
                WHERE id = %(round_id)s
                FOR UPDATE -- this prevents SELECT-SELECT-UPDATE-UPDATE races
                """,
                RoundArg(round_id=round_id),
                RoundResult,
            )
        )
        if not result:
            msg = f"Round {round_id} not found"
            raise RuntimeError(msg)
        if result[0].recipients_selected_at is not None:
            msg = f"Round {round_id} already has recipients selected, skipping"
            logger.info(msg)
            return round_id

        class CountResult(BaseModel):
            count: int

        count_result = list(
            psycopg2_query(
                cur,
                """
                SELECT count(*) AS count
                FROM token_distribution.logs
                WHERE round_id = %(round_id)s
                """,
                RoundArg(round_id=round_id),
                CountResult,
            )
        )
        if not count_result:
            msg = f"Could not fetch logs count for round {round_id}"
            raise RuntimeError(msg)
        if count_result[0].count > 0:
            msg = f"Round {round_id} already has recipients determined, yet its recipients_selected_at is NULL"
            raise RuntimeError(msg)

        for entry in round_data.leaderboard:
            psycopg2_query(
                cur,
                """
                INSERT INTO token_distribution.logs (round_id, fid, points)
                VALUES (%(round_id)s, %(fid)s, %(points)s)
                """,
                InsertArgs(
                    round_id=round_id,
                    fid=entry.fid,
                    points=entry.score,
                ),
            )

        # Mark recipients as selected
        psycopg2_query(
            cur,
            """
            UPDATE token_distribution.rounds
            SET recipients_selected_at = CURRENT_TIMESTAMP
            WHERE id = %(round_id)s
            """,
            RoundArg(round_id=round_id),
        )

        logger.info(
            f"Inserted {len(round_data.leaderboard)} leaderboard entries "
            f"for round {round_id}"
        )

    return round_data.round.id


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


def calculate(round_id: UUID) -> UUID:
    """
    Calculate distribution amounts and update existing log entries.

    Queries logs from the database (inserted by collect_round_data), calculates
    amounts based on the distribution method, then updates the logs atomically.
    Receiver addresses are looked up later in submit_txs().

    :param round_id: Round ID to calculate distributions for.
    :returns: Round ID.
    """

    # Fetch round and request info
    class RoundQueryArgs(BaseModel):
        round_id: UUID

    with (
        get_supabase_psycopg2_client() as conn,
        psycopg2_cursor(conn, commit="on_success") as cur,
    ):
        round_query = """
        SELECT r.id, r.amount, r.method, req.round_method
        FROM token_distribution.rounds r
        JOIN token_distribution.requests req ON r.request_id = req.id
        WHERE r.id = %(round_id)s
        FOR UPDATE -- this prevents SELECT-SELECT-UPDATE-UPDATE races
        """

        class RoundInfo(BaseModel):
            id: UUID
            amount: int
            method: RoundMethod | None
            round_method: RoundMethod

        for round_info in psycopg2_query(
            cur, round_query, RoundQueryArgs(round_id=round_id), RoundInfo
        ):
            break
        else:
            raise ValueError(f"Round {round_id} not found")

        amount = round_info.amount
        method = round_info.method or round_info.round_method

        # Fetch existing logs (fid and points) from the database
        log_query = """
        SELECT id, fid, points, amount
        FROM token_distribution.logs
        WHERE round_id = %(round_id)s
        ORDER BY id
        FOR UPDATE -- lock rows so their amounts can't be changed by other tasks
        """

        class LogEntry(BaseModel):
            id: UUID
            fid: int
            points: int
            amount: Decimal | None

        log_entries = list(
            psycopg2_query(cur, log_query, RoundQueryArgs(round_id=round_id), LogEntry)
        )

        if not log_entries:
            logger.info(f"No log entries for round {round_id}, nothing to calculate")
            return round_id

        num_filled = sum(1 for entry in log_entries if entry.amount is not None)
        if num_filled == len(log_entries):
            logger.info(f"Round {round_id} has all logs filled, skipping")
            return round_id
        elif num_filled > 0:
            # breaks all-or-none invariant
            msg = f"Round {round_id} has partially filled logs"
            raise RuntimeError(msg)

        # Define weight function based on method
        match method:
            case RoundMethod.PROPORTIONAL:

                def get_weight(entry: LogEntry) -> int:
                    return entry.points
            case RoundMethod.UNIFORM:

                def get_weight(_entry: LogEntry) -> int:
                    return 1
            case _:
                raise ValueError(f"Unknown distribution method: {method}")

        total_weight = sum(get_weight(entry) for entry in log_entries)

        # Calculate distribution amounts
        class UpdateArgs(BaseModel):
            id: UUID
            amount: int

        distributions: list[UpdateArgs] = []
        cumulative_weight = 0
        cumulative_amount = 0

        for entry in log_entries:
            cumulative_weight += get_weight(entry)
            dist_amount = (
                amount * cumulative_weight // (total_weight or 1) - cumulative_amount
            )
            cumulative_amount += dist_amount
            distributions.append(UpdateArgs(id=entry.id, amount=dist_amount))

        if total_weight > 0:
            assert cumulative_weight == total_weight
            assert cumulative_amount == amount

        for dist in distributions:
            psycopg2_query(
                cur,
                """
                UPDATE token_distribution.logs
                SET amount = %(amount)s
                WHERE id = %(id)s
                """,
                dist,
            )

        logger.info(
            f"Updated {len(distributions)} distribution amounts for round {round_id} "
            f"using {method} method"
        )

    return round_id


def verify(round_id: UUID) -> UUID:
    """
    Verify that calculated distributions match the round budget.

    Queries logs from the database and verifies:
    1. Sum of amounts matches the round amount (or is NULL for empty rounds)
    2. The number of recipients doesn't exceed the configured maximum

    :param round_id: Round ID to verify.
    :returns: Round ID.
    :raises ValueError: If validation fails.
    """

    class RoundQueryArgs(BaseModel):
        round_id: UUID

    with get_supabase_psycopg2_client() as conn, psycopg2_cursor(conn) as cur:
        query = """
        WITH
            computed AS (
                SELECT
                    sum(amount) AS amount,
                    count(*) AS count
                FROM token_distribution.logs
                WHERE round_id = %(round_id)s
            ), configured AS (
                SELECT
                    r.amount,
                    COALESCE(r.num_recipients, req.num_recipients_per_round) AS max_count
                FROM token_distribution.rounds AS r
                JOIN token_distribution.requests AS req ON r.request_id = req.id
                WHERE r.id = %(round_id)s
            )
        SELECT
            computed.amount AS computed_amount,
            configured.amount AS configured_amount,
            computed.count AS num_recipients,
            configured.max_count AS max_recipients
        FROM computed, configured
        """

        class VerificationResult(BaseModel):
            computed_amount: int | None
            configured_amount: int
            num_recipients: int
            max_recipients: int

        for result in psycopg2_query(
            cur, query, RoundQueryArgs(round_id=round_id), VerificationResult
        ):
            break
        else:
            raise ValueError(f"Round {round_id} not found")

    # Check amount match (NULL is OK for empty rounds)
    if (
        result.computed_amount is not None
        and result.computed_amount != result.configured_amount
    ):
        error_msg = (
            f"Amount mismatch for round {round_id}: "
            f"expected {result.configured_amount}, computed {result.computed_amount}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Check the recipient count
    if result.num_recipients > result.max_recipients:
        error_msg = (
            f"Recipient count exceeds limit for round {round_id}: "
            f"{result.num_recipients} > {result.max_recipients}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"Verification passed for round {round_id}: "
        f"{result.computed_amount or 0} tokens to {result.num_recipients} recipients "
        f"(max {result.max_recipients})"
    )

    return round_id


def lookup_recipients(round_id: UUID) -> UUID:
    """
    Look up and populate receiver addresses for a round's log entries.

    Queries logs with NULL receiver addresses, fetches wallet addresses from
    profiles, and updates the logs. Each row is committed independently for
    idempotency on retry.

    :param round_id: Round ID to look up recipients for.
    :returns: Round ID.
    """

    # Look up and update receiver addresses (auto-commit each row)
    with (
        get_supabase_psycopg2_client() as conn,
        psycopg2_cursor(conn, commit="auto") as cur,
    ):

        class RoundQueryArgs(BaseModel):
            round_id: UUID

        log_query_for_address = """
        SELECT id, fid
        FROM token_distribution.logs
        WHERE round_id = %(round_id)s
          AND receiver IS NULL
        ORDER BY id
        """

        class LogForAddress(BaseModel):
            id: UUID
            fid: int

        logs_need_address = list(
            psycopg2_query(
                cur,
                log_query_for_address,
                RoundQueryArgs(round_id=round_id),
                LogForAddress,
            )
        )

        if not logs_need_address:
            logger.info(f"No addresses to look up for round {round_id}")
            return round_id

        fids = [log.fid for log in logs_need_address]
        wallet_addresses = asyncio.run(get_wallet_addresses_async(fids))

        class UpdateReceiverArgs(BaseModel):
            id: UUID
            receiver: EthAddress | None

        for log in logs_need_address:
            receiver = wallet_addresses.get(log.fid)
            if receiver is None:
                continue  # in case of UPDATE races, avoid clobbering with None
            psycopg2_query(
                cur,
                """
                UPDATE token_distribution.logs
                SET receiver = %(receiver)s
                WHERE id = %(id)s AND receiver IS NULL
                """,
                UpdateReceiverArgs(id=log.id, receiver=receiver),
            )
            if cur.rowcount == 0:
                # SELECT-SELECT-UPDATE-UPDATE race - at least we have an address to use,
                # so this is not fatal.
                logger.warning(f"Log {log.id} already has a receiver address")

        logger.info(
            f"Updated {len(logs_need_address)} receiver addresses for round {round_id}"
        )

    return round_id


def submit_txs(round_ids: Iterable[UUID]) -> Iterable[UUID]:
    """
    Submit blockchain transactions for all verified distributions.

    Validates funding and submits transactions. Receiver addresses should already
    be populated by lookup_recipients(). This task handles all transactions serially
    to manage nonce properly. Each TX hash is committed independently for idempotency.

    :param round_ids: Round IDs to submit transactions for.
    :returns: Round IDs that were processed (passthrough).
    """

    for round_id in round_ids:
        yield round_id  # passthrough

        # Fetch round and request data from DB
        class RoundQueryArgs(BaseModel):
            round_id: UUID

        with (
            get_supabase_psycopg2_client() as conn,
            psycopg2_cursor(conn) as cur,
        ):
            query = """
            SELECT r.id, r.amount, req.chain_id, req.token_address
            FROM token_distribution.rounds r
            JOIN token_distribution.requests req ON r.request_id = req.id
            WHERE r.id = %(round_id)s
            """

            class RoundWithRequest(BaseModel):
                id: UUID
                amount: int
                chain_id: int
                token_address: EthAddress

            for row in psycopg2_query(
                cur, query, RoundQueryArgs(round_id=round_id), RoundWithRequest
            ):
                break
            else:
                logger.warning(f"Round {round_id} not found, skipping")
                continue

        # Validate funding
        if not validate_funding(round_id, row.amount):
            logger.info(f"Skipping round {round_id} due to insufficient funding")
            continue

        logger.info(f"Processing round {round_id}")

        # Submit transactions (auto-commit each TX hash to prevent double-payment on retry)
        with (
            get_supabase_psycopg2_client() as conn,
            psycopg2_cursor(conn, commit="auto") as cur,
        ):
            # Fetch logs that need TX submission
            log_query = """
            SELECT id, receiver, amount
            FROM token_distribution.logs
            WHERE round_id = %(round_id)s
              AND tx_hash IS NULL
              AND receiver IS NOT NULL
              AND amount IS NOT NULL
            ORDER BY id
            """

            class LogForTx(BaseModel):
                id: UUID
                receiver: EthAddress
                amount: int

            logs = list(
                psycopg2_query(
                    cur, log_query, RoundQueryArgs(round_id=round_id), LogForTx
                )
            )

            if not logs:
                logger.info(f"No logs to submit for round {round_id}")
                continue

            # Initialize Web3
            w3 = Web3(Web3.HTTPProvider(rpc_for_chain_id(row.chain_id)))
            account = w3.eth.account.from_key(
                settings.CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY.get_secret_value()
            )
            sign_and_send_raw_middleware = SignAndSendRawMiddlewareBuilder.build(
                account
            )
            w3.middleware_onion.inject(sign_and_send_raw_middleware, layer=0)
            w3.eth.default_account = account.address
            contract = w3.eth.contract(address=row.token_address, abi=ERC20_ABI)

            # Get current nonce
            nonce = w3.eth.get_transaction_count(account.address, "pending")

            for log in logs:
                logger.debug(f"Processing log {log.id}")

                # Build transfer data using "transfer(address to, uint256 amount)"
                tx_hash: HexBytes = contract.functions.transfer(
                    log.receiver, log.amount
                ).transact({"chainId": row.chain_id, "nonce": nonce, "gas": 100000})

                try:
                    logger.debug(f"Submitted tx {to_hex(tx_hash)} for log {log.id}")

                    # Update the log with tx hash (only if not already set - race detection)
                    class UpdateArgs(BaseModel):
                        id: UUID
                        tx_hash: TxHash

                    cur.execute(
                        """
                        UPDATE token_distribution.logs
                        SET tx_hash = %(tx_hash)s
                        WHERE id = %(id)s
                          AND tx_hash IS NULL
                        """,
                        UpdateArgs(id=log.id, tx_hash=to_hex(tx_hash)).model_dump(),
                    )

                    if cur.rowcount == 0:
                        # TODO(ek) - try to supersede/cancel the duplicate TX
                        # Send a null TX (e.g., 0 ETH self-transfer) with the same nonce and
                        # 2x gas price to supersede the duplicate. Poll both TX receipts with timeout.
                        # Only one will confirm (nonce conflict). If replacement confirms: another
                        # task instance is racing us (likely ahead on subsequent logs), so abort
                        # this instance and let the winner continue. If original confirms: double-
                        # payment occurred, raise exception for manual intervention.
                        raise RuntimeError(
                            f"DOUBLE-PAYMENT RACE DETECTED: log {log.id} already has a tx_hash! "
                            f"Would-be TX hash: {to_hex(tx_hash)}.  Please mitigate."
                        )

                    nonce += 1

                except Exception:
                    logger.warning(
                        f"Failed to record TX hash for log {log.id}. "
                        f"TX hash (DO NOT LOSE THIS): {to_hex(tx_hash)}"
                    )
                    raise

            logger.info(f"Submitted {len(logs)} transactions for round {round_id}")


def wait_for_confirmations(round_ids: Iterable[UUID]) -> Iterable[UUID]:
    """
    Wait for all transaction confirmations on the blockchain.

    Query the database for logs with pending transactions (`tx_hash IS NOT NULL
    AND tx_status IS NULL`) and wait for confirmation. Update tx_status upon
    confirmation, then mark the round as fulfilled. Idempotent - skip already-confirmed
    transactions on retry.

    :param round_ids: Round IDs to wait for confirmations.
    :return: Round IDs that were processed (passthrough).
    :raises ValueError: If any transaction is reverted.
    :raises TimeoutError: If the transaction is not confirmed within timeout.
    """

    with (
        get_supabase_psycopg2_client() as conn,
        psycopg2_cursor(conn, commit="on_success") as cur,
    ):
        for round_id in round_ids:
            yield round_id  # passthrough

            # Fetch chain_id for this round
            class RoundQueryArgs(BaseModel):
                round_id: UUID

            query = """
            SELECT req.chain_id
            FROM token_distribution.rounds r
            JOIN token_distribution.requests req ON r.request_id = req.id
            WHERE r.id = %(round_id)s
            FOR NO KEY UPDATE OF r SKIP LOCKED -- prevent SELECT-SELECT-UPDATE-UPDATE races
            """

            class ChainInfo(BaseModel):
                chain_id: int

            for chain_info in psycopg2_query(
                cur, query, RoundQueryArgs(round_id=round_id), ChainInfo
            ):
                break
            else:
                logger.warning(
                    f"Round {round_id} not found or already being processed, skipping"
                )
                continue

            # Initialize Web3
            w3 = Web3(Web3.HTTPProvider(rpc_for_chain_id(chain_info.chain_id)))

            # Fetch pending transactions (tx_hash set but tx_status null)
            class PendingTx(BaseModel):
                id: UUID
                tx_hash: TxHash

            for pending_tx in psycopg2_query(
                cur,
                """
                SELECT id, tx_hash
                FROM token_distribution.logs
                WHERE round_id = %(round_id)s
                  AND tx_hash IS NOT NULL
                  AND tx_status IS NULL
                ORDER BY id
                    FOR NO KEY UPDATE SKIP LOCKED -- of tx_status later
                """,
                RoundQueryArgs(round_id=round_id),
                PendingTx,
            ):
                tx_hash = pending_tx.tx_hash
                log_id = pending_tx.id

                for attempt, tick in enumerate(
                    ticks_until_timeout(
                        settings.TX_CONFIRMATION_TIMEOUT,
                        settings.TX_CONFIRMATION_INTERVAL,
                        # Most TXs in a batch should be available immediately, optimize for it.
                        delay_start=False,
                        skip_clumped=True,
                    )
                ):
                    logger.debug(
                        f"checking {tx_hash} ({attempt=} scheduled at {tick=})"
                    )
                    try:
                        receipt = w3.eth.get_transaction_receipt(tx_hash)
                    except TransactionNotFound:
                        continue
                    break
                else:
                    raise TimeoutError(
                        f"Transaction {tx_hash} not confirmed in {settings.TX_CONFIRMATION_TIMEOUT}"
                    )

                tx_status = receipt["status"]
                block_number = receipt["blockNumber"]

                # Update tx_status in DB
                class UpdateStatusArgs(BaseModel):
                    id: UUID
                    tx_status: int

                psycopg2_query(
                    cur,
                    """
                    UPDATE token_distribution.logs
                    SET tx_status = %(tx_status)s
                    WHERE id = %(id)s AND tx_status IS NULL
                    """,
                    UpdateStatusArgs(id=log_id, tx_status=tx_status),
                )
                if cur.rowcount == 0:
                    # We had already locked the row, so this shouldn't have happened!
                    logger.warning(
                        f"Locked {log_id=} changed or disappeared under our nose!"
                    )

                if tx_status == 1:
                    logger.info(f"TX {tx_hash} confirmed in block {block_number}")
                else:
                    logger.warning(f"TX {tx_hash} was reverted! {receipt=}")

            # Mark round as fulfilled after all TXs confirmed
            psycopg2_query(
                cur,
                """
                UPDATE token_distribution.rounds
                SET fulfilled_at = CURRENT_TIMESTAMP
                WHERE id = %(round_id)s
                """,
                RoundQueryArgs(round_id=round_id),
            )
            logger.info(f"Round {round_id} marked as fulfilled")

    logger.info(f"All transactions confirmed successfully")


def notify_recipients(round_ids: list[UUID]) -> None:
    """Send notifications to all recipients who received rewards.

    Notification message format:
    - With token_symbol: "Your trades & casts for {TOKEN} paid off. You've earned
      an airdrop from the Believer Leaderboard. Check rank"
    - Without token_symbol: "Your trades & casts paid off. You've earned an airdrop
      from the Believer Leaderboard. Check rank"

    Target URL: ``https://cura.network/{token_address}/leaderboard?category=believers``

    :param round_ids: List of round IDs to send notifications for.
    """
    if not round_ids:
        logger.info("No rounds to send notifications for")
        return

    logger.info(f"Sending notifications for {len(round_ids)} rounds")

    # Query database to get FIDs and metadata for confirmed logs (tx_status = 1)
    with (
        get_supabase_psycopg2_client() as conn,
        psycopg2_cursor(conn) as cur,
    ):

        class LogQueryArgs(BaseModel):
            round_ids: list[UUID]

        class LogQueryRow(BaseModel):
            round_id: UUID
            token_address: EthAddress
            fids: list[int]
            round_metadata: JSON
            request_metadata: JSON

        rounds_data = list(
            psycopg2_query(
                cur,
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
                WHERE l.round_id = ANY(%s::uuid[])
                  AND l.tx_status = 1
                GROUP BY l.round_id, req.token_address, r.metadata, req.metadata
                """,
                LogQueryArgs(round_ids=round_ids),
                LogQueryRow,
            )
        )

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
            round_id = round_data.round_id
            fids = round_data.fids
            token_address = round_data.token_address

            # Extract token_symbol from metadata
            # Check round_metadata first, then request_metadata
            token_symbol = None

            if isinstance(round_data.round_metadata, dict):
                token_symbol = round_data.round_metadata.get("token_symbol")

            if not token_symbol and isinstance(round_data.request_metadata, dict):
                token_symbol = round_data.request_metadata.get("token", {}).get(
                    "symbol"
                )

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

    total_recipients = sum(len(rd["fids"]) for rd in rounds_data)
    logger.info(
        f"Successfully sent notifications for {len(rounds_data)} rounds "
        f"covering {total_recipients} recipients"
    )

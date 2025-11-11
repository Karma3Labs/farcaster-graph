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
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import List

import aiohttp
import asyncpg
import niquests
from eth_typing import ChecksumAddress
from eth_utils import to_bytes, to_checksum_address
from hexbytes import HexBytes
from psycopg2.extras import RealDictCursor
from urllib3.util import Retry
from web3 import Web3
from web3.exceptions import TransactionNotFound

import cura_utils
from config import settings
from db_utils import get_supabase_psycopg2_client

logger = logging.getLogger(__name__)


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


def validate_funding(round_id: str, amount: Decimal) -> bool:
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
        WHERE id = %s
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
    SELECT
        funded,
        scheduled,
        funded - scheduled as available,
        %s as requested
    FROM total_funded, already_scheduled
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (round_id, amount))
            result = cur.fetchone()

            if not result:
                logger.error(f"Could not fetch funding info for round {round_id}")
                return False

            funded, scheduled, available, requested = result

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


def get_last_successful_round_timestamp(round_id: str) -> datetime:
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
            last_timestamp = result[0] if result and result[0] else datetime(2000, 1, 1)
            logger.info(
                f"Last successful round timestamp for {round_id}: {last_timestamp}"
            )
            return last_timestamp


def gather_rounds_due(execution_date: datetime) -> list[str]:
    """
    Gather all rounds that are due for processing as of the execution date.

    :param execution_date: Datetime object representing the DAG execution date
    :returns: List of round UUID strings that need processing
    """
    query = """
    SELECT r.id
    FROM token_distribution.rounds r
    LEFT JOIN token_distribution.logs l ON r.id = l.round_id
    WHERE r.scheduled <= %s
      AND l.id IS NULL  -- No logs exist yet
    GROUP BY r.id, r.scheduled
    ORDER BY r.scheduled
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (execution_date,))
            round_ids = [str(row[0]) for row in cur.fetchall()]
            logger.info(
                f"Found {len(round_ids)} rounds due for processing as of {execution_date}"
            )
            return round_ids


async def fetch_leaderboard_async(round_id: str) -> dict:
    """
    Async function to fetch leaderboard data for a specific round.

    :param round_id: UUID string of the round
    :returns: Dict containing round_id and leaderboard data
    """
    # First, get round details
    query = """
    SELECT
        r.id AS round_id,
        r.amount,
        r.scheduled,
        COALESCE(r.method, req.round_method) AS method,
        COALESCE(r.num_recipients, req.num_recipients_per_round) AS num_recipients,
        req.token_address,
        req.chain_id
    FROM token_distribution.rounds r
    JOIN token_distribution.requests req ON r.request_id = req.id
    WHERE r.id = %s
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (round_id,))
            round_data = cur.fetchone()

            if not round_data:
                raise ValueError(f"Round {round_id} not found")

    # Convert the token address to ChecksumAddress (handles bytes/memoryview/str)
    token_address: ChecksumAddress = to_checksum_address(round_data["token_address"])

    # Get time window for leaderboard
    # Start time is the last successful round timestamp or epoch
    start_time = get_last_successful_round_timestamp(round_id)
    # End time is the current round's scheduled time
    end_time = round_data["scheduled"]

    # Fetch leaderboard from API
    api_base = "https://graph.cast.k3l.io"
    url = f"{api_base}/tokens/{token_address}/leaderboards/trader"

    # If no limit, fetch a large number (API default or max)
    limit = round_data["num_recipients"]
    actual_limit = limit if limit > 0 else 1000

    # Include time window parameters
    params = {
        "limit": actual_limit,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }

    logger.info(
        f"Fetching leaderboard for token {token_address} "
        f"from {start_time} to {end_time}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            leaderboard_data = await response.json()

            # Apply limit if specified and not unlimited
            if 0 < limit < len(leaderboard_data["result"]):
                leaderboard_data["result"] = leaderboard_data["result"][:limit]

    logger.info(
        f"Fetched {len(leaderboard_data['result'])} entries for round {round_id}, "
        f"method: {round_data['method']}, limit: {limit if limit > 0 else 'unlimited'}, "
        f"time window: {start_time} to {end_time}"
    )

    return {
        "round_id": round_id,
        "amount": str(round_data["amount"]),
        "method": round_data["method"],
        "num_recipients": round_data["num_recipients"],
        "token_address": token_address,
        "chain_id": round_data["chain_id"],
        "leaderboard": leaderboard_data["result"],
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


def fetch_leaderboard(round_id: str) -> dict:
    """
    Synchronous wrapper for fetch_leaderboard_async.

    :param round_id: UUID string of the round
    :returns: Dict containing round_id and leaderboard data
    """
    return asyncio.run(fetch_leaderboard_async(round_id))


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


def calculate(round_data: dict) -> list[str]:
    """
    Calculate distribution amounts and atomically insert into the logs.

    :param round_data: Dict containing round_id, amount, method, and leaderboard
    :returns: List of log UUID strings that were created
    """
    round_id = round_data["round_id"]
    amount = Decimal(round_data["amount"])
    method = round_data["method"]
    leaderboard = round_data["leaderboard"]

    # Check if already processed (idempotency)
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM token_distribution.logs WHERE round_id = %s",
                (round_id,),
            )
            if cur.fetchone()[0] > 0:
                logger.info(f"Round {round_id} already processed, skipping")
                # Return existing log IDs
                cur.execute(
                    "SELECT id FROM token_distribution.logs WHERE round_id = %s",
                    (round_id,),
                )
                return [str(row[0]) for row in cur.fetchall()]

    # Validate funding before proceeding
    if not validate_funding(round_id, amount):
        logger.info(f"Skipping round {round_id} due to insufficient funding")
        return []

    # Get wallet addresses for all FIDs
    fids = [entry["fid"] for entry in leaderboard]
    wallet_addresses = asyncio.run(get_wallet_addresses_async(fids))

    # Calculate distributions based on the method
    distributions = []

    # Process all entries, including those without wallet addresses
    if not leaderboard:
        logger.warning(f"No recipients for round {round_id}")
        return []

    # Count how many have wallet addresses for logging
    with_wallet_count = sum(
        1 for entry in leaderboard if wallet_addresses.get(entry["fid"])
    )
    without_wallet_count = len(leaderboard) - with_wallet_count
    if without_wallet_count > 0:
        logger.info(
            f"Round {round_id}: {with_wallet_count} users have wallets, {without_wallet_count} do not (will record with NULL receiver)"
        )

    if method == "uniform":
        # Equal distribution to all recipients
        amount_per_recipient = amount / len(leaderboard)

        for entry in leaderboard:
            wallet_address = wallet_addresses.get(
                entry["fid"]
            )  # Can be None for older accounts
            distributions.append(
                {
                    "fid": entry["fid"],
                    "wallet_address": wallet_address,
                    "amount": amount_per_recipient,
                    "points": Decimal(str(entry["score"])),
                }
            )

    elif method == "proportional":
        # Proportional distribution based on scores
        total_score = sum(entry["score"] for entry in leaderboard)

        if total_score == 0:
            logger.warning(
                f"Total score is 0 for round {round_id}, cannot distribute proportionally"
            )
            return []

        for entry in leaderboard:
            wallet_address = wallet_addresses.get(
                entry["fid"]
            )  # Can be None for older accounts
            percentage = entry["score"] / total_score
            dist_amount = amount * Decimal(str(percentage))

            distributions.append(
                {
                    "fid": entry["fid"],
                    "wallet_address": wallet_address,
                    "amount": dist_amount,
                    "points": Decimal(str(entry["score"])),
                }
            )

    else:
        raise ValueError(f"Unknown distribution method: {method}")

    # Insert all logs atomically
    log_ids = []
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            try:
                for dist in distributions:
                    # Convert ChecksumAddress to bytes for database storage, or None for NULL
                    receiver_bytes = (
                        to_bytes(hexstr=dist["wallet_address"])
                        if dist["wallet_address"]
                        else None
                    )

                    cur.execute(
                        """
                        INSERT INTO token_distribution.logs
                        (round_id, receiver, amount, tx_hash, fid, points)
                        VALUES (%s, %s, %s, NULL, %s, %s)
                        RETURNING id
                    """,
                        (
                            round_id,
                            receiver_bytes,
                            dist["amount"],
                            dist["fid"],
                            dist["points"],
                        ),
                    )

                    log_id = cur.fetchone()[0]
                    log_ids.append(str(log_id))

                conn.commit()
                logger.info(
                    f"Created {len(log_ids)} distribution logs for round {round_id} "
                    f"using {method} method"
                )

            except Exception as e:
                conn.rollback()
                logger.error(
                    f"Failed to insert logs for round {round_id}: {e}", exc_info=True
                )
                raise

    return log_ids


def verify(log_ids: list[str], round_id: str) -> list[str]:
    """
    Verify that calculated distributions match the round budget.

    :param log_ids: List of log UUID strings to verify
    :param round_id: UUID string of the round
    :returns: List of log UUID strings (pass-through for next task)
    :raises ValueError: If the calculated amount doesn't match the expected amount
    """
    if not log_ids:
        logger.info(f"No logs to verify for round {round_id}")
        return log_ids

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            # Get expected amount from round
            cur.execute(
                "SELECT amount FROM token_distribution.rounds WHERE id = %s",
                (round_id,),
            )
            expected_amount = cur.fetchone()[0]

            # Sum up calculated logs
            cur.execute(
                """
                SELECT SUM(amount) FROM token_distribution.logs
                WHERE id = ANY(%s::uuid[])
            """,
                (log_ids,),
            )
            actual_amount = cur.fetchone()[0] or Decimal("0")

            # Allow a small rounding difference (0.01)
            difference = abs(expected_amount - actual_amount)
            if difference > Decimal("0.01"):
                error_msg = (
                    f"Amount mismatch for round {round_id}: "
                    f"expected {expected_amount}, calculated {actual_amount}, "
                    f"difference {difference}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(
                f"Verification passed for round {round_id}: "
                f"{actual_amount} tokens to {len(log_ids)} recipients"
            )

    return log_ids


def submit_txs(log_ids_nested: list[list[str]]) -> list[HexBytes]:
    """
    Submit blockchain transactions for all verified distributions.

    This task handles all transactions serially to manage nonce properly.

    :param log_ids_nested: Nested list of log UUID strings from multiple rounds
    :returns: List of transaction hashes as HexBytes
    """
    # Flatten nested lists
    all_log_ids = [log_id for sublist in log_ids_nested for log_id in sublist]

    if not all_log_ids:
        logger.info("No logs to submit transactions for")
        return []

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))
    account = w3.eth.account.from_key(
        settings.CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY.get_secret_value()
    )

    # Get current nonce
    nonce = w3.eth.get_transaction_count(account.address, "pending")

    tx_hashes: list[HexBytes] = []
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            # Fetch logs needing submission (excluding NULL receivers)
            cur.execute(
                """
                SELECT l.id, l.receiver, l.amount, req.token_address
                FROM token_distribution.logs l
                JOIN token_distribution.rounds r ON l.round_id = r.id
                JOIN token_distribution.requests req ON r.request_id = req.id
                WHERE l.id = ANY(%s::uuid[])
                  AND l.tx_hash IS NULL
                  AND l.receiver IS NOT NULL  -- Skip users without wallet addresses
                ORDER BY l.id
            """,
                (all_log_ids,),
            )

            logs_to_submit = cur.fetchall()

            # Count logs with NULL receivers
            cur.execute(
                """
                SELECT COUNT(*)
                FROM token_distribution.logs l
                JOIN token_distribution.rounds r ON l.round_id = r.id
                WHERE l.id = ANY(%s::uuid[])
                  AND l.receiver IS NULL
            """,
                (all_log_ids,),
            )
            null_receiver_count = cur.fetchone()[0]

            if null_receiver_count > 0:
                logger.info(
                    f"Skipping {null_receiver_count} distributions with NULL receivers (users without wallets)"
                )

            if not logs_to_submit:
                logger.info("No logs with valid receivers to submit transactions for")
                return []

            logger.info(f"Submitting {len(logs_to_submit)} transactions")

            for log_id, receiver, amount, token_address in logs_to_submit:
                # Build ERC20 transfer transaction
                # This assumes token_address is an ERC20 token
                # Would need to handle native token transfers differently

                # Convert receiver bytes and token bytes to ChecksumAddress
                receiver_address: ChecksumAddress = to_checksum_address(receiver)
                token_address_checksum: ChecksumAddress = to_checksum_address(
                    token_address
                )

                # Build transfer data using "transfer(address to, uint256 amount)"
                transfer_data = (
                    "0xa9059cbb"  # transfer method ID
                    + receiver_address[2:].zfill(64)  # to address
                    + hex(int(amount))[2:].zfill(64)  # amount (already in raw uint256)
                )

                # Build transaction
                tx = {
                    "nonce": nonce,
                    "to": token_address_checksum,
                    "data": transfer_data,
                    "gas": 100000,  # Estimate in production
                    "gasPrice": w3.eth.gas_price,
                    "chainId": settings.CHAIN_ID,
                }

                # Sign and send
                signed_tx = account.sign_transaction(tx)
                tx_hash: HexBytes = w3.eth.send_raw_transaction(
                    signed_tx.rawTransaction
                )

                # Update the log with tx hash (store as bytes in the database)
                cur.execute(
                    """
                    UPDATE token_distribution.logs
                    SET tx_hash = %s
                    WHERE id = %s
                """,
                    (bytes(tx_hash), log_id),
                )

                tx_hashes.append(tx_hash)
                nonce += 1

                logger.info(f"Submitted tx {tx_hash.to_0x_hex()} for log {log_id}")

            conn.commit()

    return tx_hashes


def wait_for_confirmations(tx_hashes: list[HexBytes]) -> None:
    """
    Wait for all transaction confirmations on the blockchain.

    :param tx_hashes: List of transaction hashes as HexBytes.
    :raises ValueError: If any transaction is reverted.
    :raises TimeoutError: If the transaction is not confirmed within timeout.
    """
    if not tx_hashes:
        logger.info("No transactions to wait for")
        return

    logger.info(f"Waiting for {len(tx_hashes)} transaction confirmations")

    w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))

    for tx_hash in tx_hashes:
        retries = 0
        max_retries = 60  # 5 minutes with 5-second intervals

        while retries < max_retries:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt["status"] == 1:
                    logger.info(
                        f"TX {tx_hash.to_0x_hex()} confirmed in block {receipt['blockNumber']}"
                    )
                    break
                else:
                    raise ValueError(f"Transaction {tx_hash.to_0x_hex()} was reverted!")
            except TransactionNotFound:
                retries += 1
                time.sleep(5)

        if retries >= max_retries:
            raise TimeoutError(
                f"Transaction {tx_hash.to_0x_hex()} not confirmed after {max_retries * 5} seconds"
            )

    logger.info("All transactions confirmed successfully")


def notify_recipients(log_ids_nested: list[list[str]]) -> None:
    """Send notifications to all recipients who received rewards.

    Notification message format:
    - With token_symbol: "Your trades & casts for {TOKEN} paid off. You've earned
      an airdrop from the Believer Leaderboard. Check rank"
    - Without token_symbol: "Your trades & casts paid off. You've earned an airdrop
      from the Believer Leaderboard. Check rank"

    Target URL: ``https://cura.network/{token_address}/leaderboard?category=believers``

    :param log_ids_nested: Nested list of log UUID strings from multiple rounds
    """
    # Flatten nested lists
    all_log_ids = [log_id for sublist in log_ids_nested for log_id in sublist]

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
        logger.warning("No round data found for notification logs")
        return

    # Setup HTTP session for notifications
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
                body = f"Your trades & casts for {token_symbol} paid off. Check rank"
            else:
                body = "Your trades & casts paid off. Check rank"
                logger.info(
                    f"No token_symbol found in metadata for round {round_id}, using generic message"
                )

            # Generate unique notification_id using round_id and token_address
            notification_id = hashlib.sha256(
                f"token-distribution-{round_id}-{token_address}".encode("utf-8")
            ).hexdigest()

            # Generate target URL with token address
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

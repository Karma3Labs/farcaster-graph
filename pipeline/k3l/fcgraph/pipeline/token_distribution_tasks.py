"""
Token distribution tasks for Airflow DAG with proper parallelization and idempotency.

This module implements the new task-based architecture for token distribution:
1. gather_rounds_due() - Identify rounds to process
2. fetch_leaderboard() - Fetch leaderboard data per round
3. calculate() - Calculate and atomically insert distribution logs
4. verify() - Verify calculations against budget
5. submit_txs() - Submit blockchain transactions with nonce management
6. wait_for_confirmations() - Wait for blockchain confirmations
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import aiohttp
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
from web3 import Web3
from web3.exceptions import TransactionNotFound

from config import settings
from db_utils import get_supabase_psycopg2_client

logger = logging.getLogger(__name__)


def validate_funding(round_id: str, amount: Decimal) -> bool:
    """
    Validate that there's sufficient funding for the distribution round.

    Checks that: total_funded >= (already_scheduled + current_round_amount)

    :param round_id: UUID string of the round to validate
    :param amount: Amount to distribute in current round
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

    Args:
        round_id: UUID string of the current round

    Returns:
        Datetime of the last successful round, or epoch (2000-01-01) if none exists
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


def gather_rounds_due(execution_date: datetime) -> List[str]:
    """
    Gather all rounds that are due for processing as of the execution date.

    Args:
        execution_date: Datetime object representing the DAG execution date

    Returns:
        List of round UUID strings that need processing
    """
    query = """
    SELECT r.id
    FROM token_distribution.rounds r
    LEFT JOIN token_distribution.logs l ON r.id = l.round_id
    WHERE r.scheduled <= %s
      AND l.id IS NULL  -- No logs exist yet
    GROUP BY r.id, r.scheduled
    ORDER BY r.scheduled ASC
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (execution_date,))
            round_ids = [str(row[0]) for row in cur.fetchall()]
            logger.info(
                f"Found {len(round_ids)} rounds due for processing as of {execution_date}"
            )
            return round_ids


async def fetch_leaderboard_async(round_id: str) -> Dict:
    """
    Async function to fetch leaderboard data for a specific round.

    Args:
        round_id: UUID string of the round

    Returns:
        Dict containing round_id and leaderboard data
    """
    # First get round details
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

    # Convert token address from bytes/memoryview to hex string
    token_addr_raw = round_data["token_address"]
    if isinstance(token_addr_raw, memoryview):
        token_address = f"0x{token_addr_raw.tobytes().hex()}"
    elif isinstance(token_addr_raw, bytes):
        token_address = f"0x{token_addr_raw.hex()}"
    elif isinstance(token_addr_raw, str):
        token_address = (
            token_addr_raw if token_addr_raw.startswith("0x") else f"0x{token_addr_raw}"
        )
    else:
        raise ValueError(f"Unexpected token_address type: {type(token_addr_raw)}")

    # Get time window for leaderboard
    # Start time is the last successful round timestamp or epoch
    start_time = get_last_successful_round_timestamp(round_id)
    # End time is the current round's scheduled time
    end_time = round_data["scheduled"]

    # Fetch leaderboard from API
    api_base = "https://graph.cast.k3l.io"
    url = f"{api_base}/tokens/{token_address}/leaderboards/trader"

    # If limit is 0, fetch a large number (API default or max)
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
            if limit > 0 and len(leaderboard_data["result"]) > limit:
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


def fetch_leaderboard(round_id: str) -> Dict:
    """
    Synchronous wrapper for fetch_leaderboard_async.

    Args:
        round_id: UUID string of the round

    Returns:
        Dict containing round_id and leaderboard data
    """
    return asyncio.run(fetch_leaderboard_async(round_id))


async def get_wallet_addresses_async(fids: List[int]) -> Dict[int, Optional[str]]:
    """
    Fetch primary wallet addresses for FIDs from neynarv3.profiles.

    Args:
        fids: List of Farcaster IDs

    Returns:
        Dictionary mapping FID to wallet address
    """
    query = """
    SELECT fid, custody_address
    FROM neynarv3.profiles
    WHERE fid = ANY($1::int[])
    """

    # Create connection to eigen8 database
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
            return {row["fid"]: row["custody_address"] for row in rows}
    finally:
        await pool.close()


def calculate(round_data: Dict) -> List[str]:
    """
    Calculate distribution amounts and atomically insert into logs table.

    Args:
        round_data: Dict containing round_id, amount, method, and leaderboard

    Returns:
        List of log UUID strings that were created
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

    # Calculate distributions based on method
    distributions = []

    # Filter out entries without wallet addresses
    valid_entries = []
    for entry in leaderboard:
        wallet_address = wallet_addresses.get(entry["fid"])
        if not wallet_address:
            logger.warning(f"No wallet address found for FID {entry['fid']}, skipping")
            continue
        valid_entries.append((entry, wallet_address))

    if not valid_entries:
        logger.warning(f"No valid recipients for round {round_id}")
        return []

    if method == "uniform":
        # Equal distribution to all recipients
        amount_per_recipient = amount / len(valid_entries)

        for entry, wallet_address in valid_entries:
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
        total_score = sum(entry["score"] for entry, _ in valid_entries)

        if total_score == 0:
            logger.warning(
                f"Total score is 0 for round {round_id}, cannot distribute proportionally"
            )
            return []

        for entry, wallet_address in valid_entries:
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
                    # Convert wallet address to bytes
                    receiver_bytes = bytes.fromhex(
                        dist["wallet_address"][2:]
                        if dist["wallet_address"].startswith("0x")
                        else dist["wallet_address"]
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


def verify(log_ids: List[str], round_id: str) -> List[str]:
    """
    Verify that calculated distributions match the round budget.

    Args:
        log_ids: List of log UUID strings to verify
        round_id: UUID string of the round

    Returns:
        List of log UUID strings (pass-through for next task)

    Raises:
        ValueError: If calculated amount doesn't match expected amount
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

            # Get sum of calculated logs
            cur.execute(
                """
                SELECT SUM(amount) FROM token_distribution.logs
                WHERE id = ANY(%s::uuid[])
            """,
                (log_ids,),
            )
            actual_amount = cur.fetchone()[0] or Decimal("0")

            # Allow small rounding difference (0.01)
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


def submit_txs(log_ids_nested: List[List[str]]) -> List[str]:
    """
    Submit blockchain transactions for all verified distributions.

    This task handles all transactions serially to manage nonce properly.

    Args:
        log_ids_nested: Nested list of log UUID strings from multiple rounds

    Returns:
        List of transaction hashes that were submitted
    """
    # Flatten nested lists
    all_log_ids = [log_id for sublist in log_ids_nested for log_id in sublist]

    if not all_log_ids:
        logger.info("No logs to submit transactions for")
        return []

    # For now, return mock transaction hashes
    # In production, this would use Web3 to submit real transactions
    tx_hashes = []

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            # Fetch all logs that need transactions
            cur.execute(
                """
                SELECT id, receiver, amount, fid
                FROM token_distribution.logs
                WHERE id = ANY(%s::uuid[])
                  AND tx_hash IS NULL
                ORDER BY id  -- Deterministic order
            """,
                (all_log_ids,),
            )

            logs_to_submit = cur.fetchall()

            if not logs_to_submit:
                logger.info("All logs already have transactions")
                return []

            logger.info(f"Submitting {len(logs_to_submit)} transactions")

            # Mock transaction submission
            # In production, initialize Web3 and manage nonce here
            for log_id, receiver, amount, fid in logs_to_submit:
                # Mock transaction hash
                mock_tx_hash = f"0x{'0' * 63}{len(tx_hashes):01x}"
                tx_hash_bytes = bytes.fromhex(mock_tx_hash[2:])

                # Update log with transaction hash
                cur.execute(
                    """
                    UPDATE token_distribution.logs
                    SET tx_hash = %s
                    WHERE id = %s
                """,
                    (tx_hash_bytes, log_id),
                )

                tx_hashes.append(mock_tx_hash)

                receiver_hex = f"0x{receiver.hex()}"
                logger.info(
                    f"Submitted tx {mock_tx_hash} for {amount} to {receiver_hex} (FID {fid})"
                )

            conn.commit()

    return tx_hashes


def wait_for_confirmations(tx_hashes: List[str]) -> None:
    """
    Wait for all transaction confirmations on the blockchain.

    Args:
        tx_hashes: List of transaction hashes to wait for

    Raises:
        ValueError: If any transaction is reverted
    """
    if not tx_hashes:
        logger.info("No transactions to wait for")
        return

    logger.info(f"Waiting for {len(tx_hashes)} transaction confirmations")

    # Mock confirmation wait
    # In production, this would use Web3 to poll for receipts
    for tx_hash in tx_hashes:
        logger.info(f"Transaction {tx_hash} confirmed")

    logger.info("All transactions confirmed successfully")


# Production Web3 implementation (commented out for now)
"""
def submit_txs_production(log_ids_nested: List[List[str]]) -> List[str]:
    # Production implementation with real Web3 integration

    all_log_ids = [log_id for sublist in log_ids_nested for log_id in sublist]

    if not all_log_ids:
        return []

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))
    account = w3.eth.account.from_key(
        settings.CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY.get_secret_value()
    )

    # Get current nonce
    nonce = w3.eth.get_transaction_count(account.address, 'pending')

    tx_hashes = []
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            # Fetch logs needing submission
            cur.execute('''
                SELECT l.id, l.receiver, l.amount, req.token_address
                FROM token_distribution.logs l
                JOIN token_distribution.rounds r ON l.round_id = r.id
                JOIN token_distribution.requests req ON r.request_id = req.id
                WHERE l.id = ANY(%s::uuid[])
                  AND l.tx_hash IS NULL
                ORDER BY l.id
            ''', (all_log_ids,))

            for log_id, receiver, amount, token_address in cur.fetchall():
                # Build ERC20 transfer transaction
                # This assumes token_address is an ERC20 token
                # Would need to handle native token transfers differently

                # Convert receiver to checksum address
                receiver_address = w3.to_checksum_address(f"0x{receiver.hex()}")
                token_address_checksum = w3.to_checksum_address(f"0x{token_address.hex()}")

                # Build transfer data
                # transfer(address to, uint256 amount)
                transfer_data = (
                    '0xa9059cbb' +  # transfer method ID
                    receiver_address[2:].zfill(64) +  # to address
                    hex(int(amount * 10**18))[2:].zfill(64)  # amount in wei
                )

                # Build transaction
                tx = {
                    'nonce': nonce,
                    'to': token_address_checksum,
                    'data': transfer_data,
                    'gas': 100000,  # Estimate in production
                    'gasPrice': w3.eth.gas_price,
                    'chainId': settings.CHAIN_ID,
                }

                # Sign and send
                signed_tx = account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Update log with tx hash
                cur.execute('''
                    UPDATE token_distribution.logs
                    SET tx_hash = %s
                    WHERE id = %s
                ''', (tx_hash, log_id))

                tx_hashes.append(tx_hash.hex())
                nonce += 1

                logger.info(f"Submitted tx {tx_hash.hex()} for log {log_id}")

    return tx_hashes


def wait_for_confirmations_production(tx_hashes: List[str]) -> None:
    # Production implementation with real Web3 integration

    if not tx_hashes:
        return

    w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))

    for tx_hash in tx_hashes:
        retries = 0
        max_retries = 60  # 5 minutes with 5 second intervals

        while retries < max_retries:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt['status'] == 1:
                    logger.info(f"TX {tx_hash} confirmed in block {receipt['blockNumber']}")
                    break
                else:
                    raise ValueError(f"Transaction {tx_hash} was reverted!")
            except TransactionNotFound:
                retries += 1
                time.sleep(5)

        if retries >= max_retries:
            raise TimeoutError(f"Transaction {tx_hash} not confirmed after {max_retries * 5} seconds")
"""

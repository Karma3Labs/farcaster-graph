#!/usr/bin/env python3
"""Test script for notify_recipients function.

This script tests the notify_recipients function using real database data
while running in test mode (no actual notifications sent).

Usage:
    python scripts/test_notify_recipients.py
    python scripts/test_notify_recipients.py --log-ids uuid1 uuid2 uuid3
    python scripts/test_notify_recipients.py --limit 5
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force test mode to prevent actual notifications
os.environ["IS_TEST"] = "true"

from loguru import logger

from config import settings
from db_utils import get_supabase_psycopg2_client
from k3l.fcgraph.pipeline.token_distribution_tasks import notify_recipients


def get_sample_log_ids(limit: int = 10) -> list[list[str]]:
    """Query database for sample log IDs.

    :param limit: Maximum number of logs to retrieve
    :return: Nested list of log UUID strings grouped by round
    """
    query = """
        SELECT
            l.id,
            l.round_id,
            l.fid,
            req.metadata->>'token_symbol' as token_symbol,
            req.token_address
        FROM token_distribution.logs l
        JOIN token_distribution.rounds r ON l.round_id = r.id
        JOIN token_distribution.requests req ON r.request_id = req.id
        ORDER BY l.round_id, l.id
        LIMIT %s
    """

    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()

            if not rows:
                logger.warning("No distribution logs found in database")
                return []

            # Group by round_id
            rounds: dict[str, list[str]] = {}
            for row in rows:
                log_id = str(row[0])
                round_id = str(row[1])
                fid = row[2]
                token_symbol = row[3]
                token_address = row[4]

                if round_id not in rounds:
                    rounds[round_id] = []
                    logger.info(
                        f"Found round {round_id} with token {token_symbol or 'N/A'}"
                    )

                rounds[round_id].append(log_id)
                logger.debug(f"  Log {log_id}: FID={fid}")

            # Convert to nested list format
            log_ids_nested = list(rounds.values())
            logger.info(
                f"Found {len(log_ids_nested)} rounds with {sum(len(r) for r in log_ids_nested)} total logs"
            )

            return log_ids_nested


def test_with_specific_log_ids(log_ids: list[str]) -> None:
    """Test with specific log IDs provided by user.

    :param log_ids: List of log UUID strings
    """
    logger.info(f"Testing with {len(log_ids)} specific log IDs")

    # Verify log IDs exist in database
    with get_supabase_psycopg2_client() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, round_id, fid
                FROM token_distribution.logs
                WHERE id = ANY(%s::uuid[])
                """,
                (log_ids,),
            )
            rows = cur.fetchall()

            if len(rows) != len(log_ids):
                logger.warning(
                    f"Only found {len(rows)}/{len(log_ids)} log IDs in database"
                )

            for row in rows:
                logger.info(f"Log {row[0]}: round={row[1]}, fid={row[2]}")

    # Group all provided IDs into a single round (for testing)
    log_ids_nested = [log_ids]

    # Execute test
    logger.info("Calling notify_recipients()...")
    notify_recipients(log_ids_nested)
    logger.info("✓ Test completed successfully")


def test_with_auto_discovery(limit: int) -> None:
    """Test by auto-discovering log IDs from database.

    :param limit: Maximum number of logs to test with
    """
    logger.info(f"Auto-discovering up to {limit} distribution logs from database...")

    log_ids_nested = get_sample_log_ids(limit)

    if not log_ids_nested:
        logger.error(
            "No distribution logs found in database. "
            "Please run the token_distribution DAG first to create test data."
        )
        sys.exit(1)

    # Execute test
    logger.info("Calling notify_recipients()...")
    notify_recipients(log_ids_nested)
    logger.info("✓ Test completed successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test notify_recipients function with real database data"
    )
    parser.add_argument(
        "--log-ids",
        nargs="+",
        help="Specific log UUIDs to test with (space-separated)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of logs to test with (default: 10)",
    )

    args = parser.parse_args()

    # Confirm test mode is enabled
    logger.info(f"IS_TEST={settings.IS_TEST}")
    logger.info(f"CURA_NOTIFY_CHUNK_SIZE={settings.CURA_NOTIFY_CHUNK_SIZE}")

    if not settings.IS_TEST:
        logger.warning(
            "WARNING: IS_TEST is not True! Notifications will be sent for real!"
        )
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Aborted")
            sys.exit(0)

    # Run test
    if args.log_ids:
        test_with_specific_log_ids(args.log_ids)
    else:
        test_with_auto_discovery(args.limit)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime
from typing import List

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from db_utils import get_supabase_client


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
def fetch_distinct_fids_from_supabase() -> List[int]:
    """Fetch distinct FIDs from Supabase fcm_registration table."""
    supabase = get_supabase_client()

    response = supabase.table("fcm_registration").select("fid").execute()

    if not response.data:
        logger.warning("No data returned from fcm_registration table")
        return []

    # Extract unique FIDs and filter out None values
    fids = list(
        set([row["fid"] for row in response.data if row.get("fid") is not None])
    )
    logger.info(f"Fetched {len(fids)} distinct FIDs from Supabase")
    return sorted(fids)


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
def update_webhook(fids: List[int]) -> None:
    """Send updated FID list to webhook endpoint."""
    payload = {
        "subscription": {
            "cast.deleted": {"minimum_author_score": 0},
            "cast.created": {
                "parent_author_fids": fids,
                "minimum_author_score": 0,
            },
            "reaction.created": {"target_fids": fids},
            "follow.created": {"target_fids": fids},
        },
        "webhook_id": "01K58G41EKAMD4FGF268ZY9BB4",
        "name": "test",
        "url": "https://notifications.cura.network/api/v1/neynar-webhook",
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.NEYNAR_API_KEY,
    }

    response = requests.put(
        settings.FCM_WEBHOOK_URL,
        json=payload,
        headers=headers,
        timeout=settings.FCM_WEBHOOK_TIMEOUT_SECS,
    )

    if response.status_code not in [200, 201, 204]:
        logger.error(f"Webhook error: {response.status_code} - {response.text}")
        raise Exception(f"Failed to update webhook: {response.status_code}")

    logger.info(f"Successfully updated webhook with {len(fids)} FIDs")


def calculate_fids_hash(fids: List[int]) -> str:
    """Calculate SHA256 hash of FID list for change detection."""
    fids_json = json.dumps(sorted(fids))
    return hashlib.sha256(fids_json.encode()).hexdigest()


def load_previous_hash(hash_file: str = "/tmp/fcm_fids_hash.txt") -> str:
    """Load previous FID hash from file."""
    try:
        with open(hash_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.info("No previous hash file found, treating as first run")
        return None
    except Exception as e:
        logger.error(f"Error reading hash file: {e}")
        return None


def save_hash(hash_value: str, hash_file: str = "/tmp/fcm_fids_hash.txt") -> None:
    """Save current FID hash to file."""
    try:
        with open(hash_file, "w") as f:
            f.write(hash_value)
        logger.info(f"Saved hash to {hash_file}")
    except Exception as e:
        logger.error(f"Error saving hash file: {e}")
        raise


def main():
    """Main function to sync FCM FIDs with webhook endpoint."""
    try:
        logger.info("Starting FCM webhook sync")

        # Fetch current FIDs from Supabase
        current_fids = fetch_distinct_fids_from_supabase()

        # Calculate hash for change detection
        current_hash = calculate_fids_hash(current_fids)

        # Get previous hash
        prev_hash = load_previous_hash()

        if current_hash == prev_hash:
            logger.info(
                f"No changes detected in FID list ({len(current_fids)} FIDs), skipping webhook update"
            )
            return

        # Update webhook with new FID list
        logger.info(
            f"FID list changed, updating webhook (previous: {prev_hash}, current: {current_hash})"
        )
        update_webhook(current_fids)

        # Store new hash
        save_hash(current_hash)

        # Log change details
        if prev_hash is None:
            logger.info(f"Initial sync: {len(current_fids)} FIDs sent to webhook")
        else:
            logger.info(f"Updated sync: {len(current_fids)} FIDs sent to webhook")

        logger.info("FCM webhook sync completed successfully")

    except Exception as e:
        logger.error(f"FCM webhook sync failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

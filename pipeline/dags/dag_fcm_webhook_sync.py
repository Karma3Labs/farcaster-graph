import hashlib
import json
from datetime import datetime, timedelta
from typing import List

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from db_utils import get_supabase_client

default_args = {
    "owner": "karma3labs",
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}


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
        "fids": fids,
        "count": len(fids),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.neynar.com/v2/farcaster/webhook/",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if response.status_code not in [200, 201, 204]:
        logger.error(f"Webhook error: {response.status_code} - {response.text}")
        raise Exception(f"Failed to update webhook: {response.status_code}")

    logger.info(f"Successfully updated webhook with {len(fids)} FIDs")


def calculate_fids_hash(fids: List[int]) -> str:
    """Calculate SHA256 hash of FID list for change detection."""
    fids_json = json.dumps(sorted(fids))
    return hashlib.sha256(fids_json.encode()).hexdigest()


with DAG(
    dag_id="fcm_webhook_sync",
    default_args=default_args,
    description="Sync FCM registration FIDs to webhook endpoint every 10 minutes",
    start_date=datetime(2025, 1, 15),
    schedule_interval=timedelta(minutes=10),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
    tags=["notifications", "fcm", "webhook"],
) as dag:

    @task(task_id="sync_fcm_webhook")
    def sync_fcm_webhook():
        """Main task to sync FCM FIDs with webhook endpoint."""
        try:
            # Fetch current FIDs from Supabase
            current_fids = fetch_distinct_fids_from_supabase()

            # Calculate hash for change detection
            current_hash = calculate_fids_hash(current_fids)

            # Get previous hash from Airflow Variable
            prev_hash = Variable.get("fcm_fids_hash", default_var=None)

            if current_hash == prev_hash:
                logger.info(
                    f"No changes detected in FID list ({len(current_fids)} FIDs), skipping webhook update"
                )
                return {
                    "status": "no_changes",
                    "fid_count": len(current_fids),
                    "hash": current_hash,
                }

            # Update webhook with new FID list
            logger.info(
                f"FID list changed, updating webhook (previous: {prev_hash}, current: {current_hash})"
            )
            update_webhook(current_fids)

            # Store new hash
            Variable.set("fcm_fids_hash", current_hash)

            # Log change details
            if prev_hash is None:
                logger.info(f"Initial sync: {len(current_fids)} FIDs sent to webhook")
            else:
                logger.info(f"Updated sync: {len(current_fids)} FIDs sent to webhook")

            return {
                "status": "updated",
                "fid_count": len(current_fids),
                "hash": current_hash,
                "previous_hash": prev_hash,
            }

        except Exception as e:
            logger.error(f"FCM webhook sync failed: {e}", exc_info=True)
            raise

    sync_fcm_webhook()

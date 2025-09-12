from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

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

    sync_fcm_webhook = BashOperator(
        task_id="sync_fcm_webhook",
        bash_command="cd /pipeline && ./run_fcm_webhook_sync.sh -w . -v .venv",
    )
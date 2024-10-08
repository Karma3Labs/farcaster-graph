from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    "extract_warpcast_followers",
    default_args=default_args,
    description="Fetch channel followers from WARPCAST API and load into DB daily",
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 8, 1),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id='extract_channel_followers',
        bash_command="cd /pipeline; extractors/extract_channel_followers.sh" 
                        " -w . -v .venv -c channels/Top_Channels.csv -s top",
        dag=dag
    )

    task1
import math
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.bash import BashOperator
from airflow.sensors.time_delta import TimeDeltaSensor
from airflow.utils.trigger_rule import TriggerRule
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

N_CHUNKS = 100  # Define the number of chunks
# NOTE: Refer to the 'k3l_channel_categories' table to get the category
CATEGORY = "test"

with DAG(
    dag_id="gen_channel_openrank",
    default_args=default_args,
    description="This runs run_globaltrust_pipeline.sh without any optimization",
    start_date=datetime(2024, 8, 16),
    # schedule_interval='0 */6 * * *',
    # schedule_interval=timedelta(hours=6),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    gen_files_task = BashOperator(
        task_id=f"gen_category_files",
        bash_command="cd /pipeline && ./run_channel_openrank.sh"
        " -w . -v .venv -t gen_category_files"
        f" -s channels/Top_Channels.csv -b channels/Bot_Fids.csv -c {CATEGORY}"
        f" -o tmp/{CATEGORY}",
        env={"PYTHONUNBUFFERED": "1"},  # Ensures real-time logging
    )
    process_task = BashOperator(
        task_id=f"process_category",
        bash_command="cd /pipeline && ./run_channel_openrank.sh"
        " -w . -v .venv -t process_category"
        f" -c {CATEGORY} -o tmp/{CATEGORY}",
        env={"PYTHONUNBUFFERED": "1"},  # Ensures real-time logging
    )
    fetch_results = BashOperator(
        task_id="fetch_results",
        bash_command="cd /pipeline && ./run_channel_openrank.sh"
        f" -w . -v .venv -t fetch_results -c {CATEGORY}"
        f" -o tmp/{CATEGORY}",
    )
    (gen_files_task >> process_task >> fetch_results)

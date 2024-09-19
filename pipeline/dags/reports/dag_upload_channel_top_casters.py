from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

PIPELINE_DIR = './'
CSV_PATH = f'{PIPELINE_DIR}/channels/Top_Channels.csv'

with DAG(
    dag_id='report_top_channel_casters',
    default_args=default_args,
    description='This backs up top caster everyday for channels into postgres db',
    start_date=datetime(2024, 8, 15),
    schedule_interval='30 20 * * *',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    fetch_dune_s3_upload_top_channel_casters = BashOperator(
        task_id='fetch_dune_s3_upload_top_channel_casters',
        bash_command="cd /pipeline && ./run_fetch_top_channel_caster.sh -v ./.venv -c {CSV_PATH}"
    )

    fetch_dune_s3_upload_top_casters


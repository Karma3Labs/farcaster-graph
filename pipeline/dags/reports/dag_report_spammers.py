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


with DAG(
    dag_id='report_spammers',
    default_args=default_args,
    description='This fetches spammers and save the list into s3',
    start_date=datetime(2024, 8, 15),
    schedule_interval='30 20 * * *',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    report_top_spammers = BashOperator(
        task_id='report_top_spammers',
        bash_command="cd /pipeline && ./run_fetch_top_spammers.sh -v ./.venv"
    )

    report_top_spammers


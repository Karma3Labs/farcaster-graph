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



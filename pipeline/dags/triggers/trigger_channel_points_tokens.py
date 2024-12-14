from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='trigger_channel_points_tokens',
    default_args=default_args,
    description='trigger channel points and tokens dags',
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval='0 0 * * *', # every day at 00:00 UTC / 16:00 PST 
    # schedule=None,
    # schedule_interval=timedelta(days=1),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    start = EmptyOperator(task_id="TODO")


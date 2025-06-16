from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='trigger_automated_casts_run',
    default_args=default_args,
    description='Periodically triggers the Cura Network automated casts every 2 hours.',
    start_date=datetime(2024, 7, 15),
    schedule_interval='0 */2 * * *',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
    tags=['notifications', 'api', 'cura'],
) as dag:

    trigger_api = BashOperator(
        task_id="trigger_cast_run_api_call",
        bash_command="curl -f -X GET https://notifications.cura.network/api/v1/casts/run",
    )
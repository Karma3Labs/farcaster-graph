from datetime import datetime, timedelta

from airflow import DAG
# from airflow.operators.empty import EmptyOperator
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
    dag_id='report_gen_metrics',
    default_args=default_args,
    description='this generates channel metrics',
    start_date=datetime(2024, 8, 15),
    schedule_interval='0 * * * *',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    # gen_channel_metrics = EmptyOperator(task_id="gen_channel_metrics")

    gen_channel_metrics = BashOperator(
        task_id='gen_channel_metrics',
        bash_command='cd /pipeline/ && ./run_channel_metrics.sh -w . -v ./.venv/ -r '
    )
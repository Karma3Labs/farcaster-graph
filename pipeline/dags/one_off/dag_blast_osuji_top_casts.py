from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}


with DAG(
    dag_id='blast_osuji_top_casts',
    default_args=default_args,
    description="Osuji.eth's top casts of all time",
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval='@daily',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    start = EmptyOperator(task_id="start_processing")

    blast = BashOperator(
            task_id="run_blast_osuji_top_casts_script",
            bash_command=("cd /pipeline && ./run_blast_osuji_top_casts.sh -w . -v .venv"),
            dag=dag)
    

    start >> blast


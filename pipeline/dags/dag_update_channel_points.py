from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
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
    dag_id='update_channel_points',
    default_args=default_args,
    description='update channel points triggered by gen_channel_ranking',
    start_date=datetime(2024, 7, 10, 18),
    # schedule_interval='*/10 * * * *',
    schedule=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    run_main = BashOperator(
        task_id="run_main",
        bash_command="cd /pipeline && ./run_fetch_top_caster.sh -v .venv",
        dag=dag)

    # TODO backup to s3
    bkup_to_s3 = EmptyOperator(task_id="bkup_to_s3")

    run_main >> bkup_to_s3


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
    dag_id='update_channel_points_v2',
    default_args=default_args,
    description='update channel points triggered by update_channel_tokens dag',
    start_date=datetime(2024, 7, 10, 18),
    # schedule_interval='0 0 * * *', # every day at 00:00 UTC / 16:00 PST 
    # schedule_interval=timedelta(days=1),
    schedule=None, # this dag is triggered by dag update_channel_tokens
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    run_main = BashOperator(
        task_id="run_main",
        bash_command="cd /pipeline && ./run_update_channel_points.sh  -w . -v .venv -t distrib",
        dag=dag)

    backup_to_s3 = BashOperator(
            task_id='backup_channel_points_bal',
            bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh backup_channel_points_bal "
        )

    run_simulation = BashOperator(
        task_id="run_simulation",
        bash_command="cd /pipeline && ./run_update_channel_points.sh  -w . -v .venv -t sim",
        dag=dag)

    run_main >> backup_to_s3 >> run_simulation


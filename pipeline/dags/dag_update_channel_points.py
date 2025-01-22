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
    schedule_interval='0 17 * * *', # every day at 17:00 UTC / 09:00 PDT 
    # schedule_interval=timedelta(days=1),
    # schedule=None, 
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    run_genesis = BashOperator(
        task_id="run_genesis",
        bash_command="cd /pipeline && ./run_update_channel_points.sh  -w . -v .venv -t genesis",
        dag=dag)
    
    daily_calc = BashOperator(
        task_id="daily_calc",
        bash_command="cd /pipeline && ./run_update_channel_points.sh  -w . -v .venv -t compute",
        dag=dag)
    
    balance_update = BashOperator(
        task_id="balance_update",
        bash_command="cd /pipeline && ./run_update_channel_points.sh  -w . -v .venv -t update",
        dag=dag)

    backup_to_s3 = BashOperator(
            task_id='backup_channel_points_bal',
            bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh backup_channel_points_bal "
        )

    run_genesis >> daily_calc >> balance_update >> backup_to_s3


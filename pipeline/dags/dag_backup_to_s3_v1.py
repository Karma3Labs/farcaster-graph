from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}


with DAG(
    dag_id='backup_to_s3_v1',
    default_args=default_args,
    description='This backs up globaltrust, localtrust and channel_ranking into s3',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='30 20 * * *',
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id='backup_globaltrust',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh globaltrust"
    )

    task2 = BashOperator(
        task_id='backup_globaltrust_config',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh globaltrust_config"
    )

    task3 = BashOperator(
        task_id='backup_localtrust',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh localtrust_v1 ~/graph_files/"
    )

    task4 = BashOperator(
        task_id='backup_channel_rank',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh channel_rank"
    )

    [task1, task2, task3, task4]


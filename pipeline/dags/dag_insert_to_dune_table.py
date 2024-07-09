from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from hooks.discord_webhook import send_alert_discord


default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': send_alert_discord,
}


with DAG(
    dag_id='insert_to_dune_tables',
    default_args=default_args,
    description='This inserts globaltrust and channel_ranking into dune',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='30 20 * * *',
    catchup=False,
) as dag:
    task4 = BashOperator(
        task_id='insert_globaltrust_to_dune',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_globaltrust_to_dune_v3"
    )

    task5 = BashOperator(
        task_id='insert_channel_rank_to_dune',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_channel_rank_to_dune_v3"
    )

    [task4, task5]


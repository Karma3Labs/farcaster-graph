from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}


with DAG(
    dag_id='backup_to_s3_v0',
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
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh localtrust"
    )

    task4 = BashOperator(
        task_id='insert_globaltrust_to_dune',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_globaltrust_to_dune"
    )

    task5 = BashOperator(
        task_id='insert_channel_rank_to_dune',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_channel_rank_to_dune"
    )

    [task1, task2, task3] >> task4 >> task5


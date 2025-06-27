from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {"owner": "coder2j", "retries": 5, "retry_delay": timedelta(minutes=2)}


with DAG(
    dag_id="one_off_migrate_dune_table",
    default_args=default_args,
    description="This backs up globaltrust, localtrust and channel_ranking into s3",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id="create_dune_globaltrust_table",
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh create_dune_globaltrust_table dataset_k3l_cast_globaltrust_v2",
    )

    [task1]

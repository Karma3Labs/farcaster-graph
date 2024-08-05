from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from hooks.discord import send_alert_discord


default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    # 'on_failure_callback': send_alert_discord,
}

# 2024-06-04 00:00
# 875822
# 2024-06-05 00:00
# 875822
# 2024-06-11 00:00
# 921037
# 2024-06-12 00:00
# 921037
# 2024-06-15 00:00
# 960387
# 2024-06-16 00:00
# 960387
with DAG(
    dag_id='dag_gen_globaltrust_by_date_v1',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval=None,
    catchup=False,
) as dag:
    push_to_dune = BashOperator(
        task_id='insert_globaltrust_to_dune_v3_f',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_globaltrust_to_dune_v3 "
    )

    task1 = BashOperator(
        task_id='06-05',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-05"
    )

    task2 = BashOperator(
        task_id='06-12',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-12"
    )

    task3 = BashOperator(
        task_id='06-16',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-16"
    )

    task5 = BashOperator(
        task_id='06-04',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-04"
    )

    task6 = BashOperator(
        task_id='06-11',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-11"
    )

    task7 = BashOperator(
        task_id='06-15',
        bash_command="cd /pipeline && ./run_globaltrust_pipeline.sh -w . -v ./.venv -d 2024-06-15 "
    )

    task1 >> task2 >> task3 >> push_to_dune >> task5 >> task6 >> task7


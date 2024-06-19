from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    'owner': 'coder2j',
    'retries': 3,
    'retry_delay': timedelta(minutes=2)
}


with DAG(
    dag_id='gen_globaltrust_v0',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='0 */6 * * *'
) as dag:
    task1 = BashOperator(
        task_id='run_globaltrust_pipeline.sh',
        bash_command="./run_globaltrust_pipeline.sh -w . -v ./.venv"
    )

    task1

    # task2 = BashOperator(
    #     task_id='second_task',
    #     bash_command="echo hey, I am task2 and will be running after task1!"
    # )

    # task3 = BashOperator(
    #     task_id='thrid_task',
    #     bash_command="echo hey, I am task3 and will be running after task1 at the same time as task2!"
    # )

    # Task dependency method 1
    # task1.set_downstream(task2)
    # task1.set_downstream(task3)

    # Task dependency method 2
    # task1 >> task2
    # task1 >> task3

    # Task dependency method 3
    # task1 >> [task2, task3]
from datetime import timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "one_off_try_airflow_features",
    default_args=default_args,
    description="One off dag to test new features",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    start = EmptyOperator(task_id="start")

    echo =  BashOperator(
        task_id="echo", 
        bash_command= "echo {{ (logical_date - macros.timedelta(days=90)) | ds }}",
        dag=dag
    )


    end = EmptyOperator(task_id="end")

    (
        start
        >> echo
        >> end
    )
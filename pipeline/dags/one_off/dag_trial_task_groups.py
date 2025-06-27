from datetime import timedelta

from airflow import DAG
from airflow.decorators import task_group
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "one_off_trial_task_groups",
    default_args=default_args,
    description="One off dag to test new features",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    @task_group(group_id="my_start_group")
    def tg_start():
        start = EmptyOperator(task_id="start")

        echo1 = BashOperator(
            task_id="echo1",
            bash_command="echo {{ (logical_date - macros.timedelta(days=90)) | ds }}",
            dag=dag,
        )

        echo2 = BashOperator(
            task_id="echo2",
            bash_command="echo '{{ prev_data_interval_end_success }}'",
            dag=dag,
        )

        start >> echo1 >> echo2

    @task_group(group_id="my_echo_group")
    def tg_echo():

        echo3 = BashOperator(
            task_id="echo3", bash_command="echo {{ macros.ds_add(ds, -90) }}", dag=dag
        )

        echo4 = BashOperator(task_id="echo4", bash_command="echo {{ ds }}", dag=dag)

        echo5 = BashOperator(
            task_id="echo5", bash_command="echo {{ logical_date }}", dag=dag
        )
        echo3 >> echo4
        echo5

    end = EmptyOperator(task_id="end")

    tg_start() >> tg_echo() >> end

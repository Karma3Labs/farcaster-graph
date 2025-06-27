import datetime
from datetime import timedelta

import pytz
from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
}


def _monday_9ampacific_in_utc_time():
    pacific_tz = pytz.timezone("US/Pacific")
    pacific_9am_str = " ".join(
        [datetime.datetime.now(pacific_tz).strftime("%Y-%m-%d"), "09:00:00"]
    )
    pacific_time = pacific_tz.localize(
        datetime.datetime.strptime(pacific_9am_str, "%Y-%m-%d %H:%M:%S")
    )
    utc_time = pacific_time.astimezone(pytz.utc)
    monday = utc_time - timedelta(days=utc_time.weekday())
    return monday


with DAG(
    dag_id="one_off_trial_branch",
    default_args=default_args,
    description="One off dag to test new features",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    @task.branch(task_id="branch")
    def branch_fn(**context):
        print(f"context: {context}")
        prev = context["prev_execution_date_success"]
        print(f"prev_execution_date_success: {prev}")
        if prev > _monday_9ampacific_in_utc_time():
            return "t2"
        return "t1"

    def empty_fn(*args, **kwargs):
        pass

    branch = branch_fn()
    t1 = EmptyOperator(task_id="t1")
    t2 = EmptyOperator(task_id="t2")

    @task_group(group_id="all_group")
    def tg_all():
        always = PythonOperator(
            task_id="always",
            python_callable=empty_fn,
            op_args=[],
            op_kwargs={},
            trigger_rule=TriggerRule.ALL_SUCCESS,
        )
        t3 = EmptyOperator(task_id="t3")

        always >> t3

    @task_group(group_id="some_group")
    def tg_some():
        always = PythonOperator(
            task_id="always",
            python_callable=empty_fn,
            op_args=[],
            op_kwargs={},
            trigger_rule=TriggerRule.ALL_SUCCESS,
        )
        sometimes = EmptyOperator(task_id="sometimes")
        t3 = EmptyOperator(task_id="t3")

        always >> sometimes >> t3

    branch >> t1 >> tg_all()
    branch >> t2 >> tg_some()

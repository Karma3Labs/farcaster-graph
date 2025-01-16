from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.decorators import task

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='one_off_trial_branch',
    default_args=default_args,
    description="One off dag to test new features",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    
    @task.branch(task_id="branch")
    def branch_fn():
        return "t1"

    branch = branch_fn()
    t1 = EmptyOperator(task_id="t1")
    t2 = EmptyOperator(task_id="t2")
    allways = EmptyOperator(task_id="allways", trigger_rule=TriggerRule.ONE_SUCCESS)
    sometimes = EmptyOperator(task_id="t3")
    t3 = EmptyOperator(task_id="t3")

    branch >> t1 
    branch >> t2

    t1 >> allways >> sometimes >> t3 
    t2 >> allways >> t3
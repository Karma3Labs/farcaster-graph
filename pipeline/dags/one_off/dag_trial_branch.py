from datetime import timedelta

from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task, task_group

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
    sometimes = EmptyOperator(task_id="sometimes")
    t3 = EmptyOperator(task_id="t3")

    @task_group(group_id='all_group')
    def tg_all():
        allways >> sometimes >> t3

    @task_group(group_id='some_group')
    def tg_some():
        sometimes >> t3

    branch >> t1 >> tg_all()
    branch >> t2 >> tg_some()


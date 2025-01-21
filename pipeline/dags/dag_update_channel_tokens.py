from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.models import DagRun
from airflow.decorators import task, task_group
from airflow.utils.state import DagRunState

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

POINTS_DAG_NAME = 'update_channel_points_v2'

with DAG(
    dag_id='update_channel_tokens',
    default_args=default_args,
    description='update channel tokens started by trigger dag or manually',
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval=timedelta(minutes=5),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    @task_group(group_id='all_group')
    def tg_all():
        prepare_airdrop = BashOperator(
            task_id="prepare_airdrop",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t prep -s airdrop -r {{ run_id }}",
            dag=dag)

        prepare_weekly = BashOperator(
            task_id="prepare_weekly",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t prep -s weekly -r {{ run_id }}",
            dag=dag)

        distribute = BashOperator(
            task_id="distribute",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t distrib",
            dag=dag)
        
        verify = BashOperator(
            task_id="verify",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t verify",
            dag=dag)
        prepare_airdrop >> prepare_weekly >> distribute >> verify


    @task_group(group_id='skip_weekly_group')
    def tg_skip_weekly():
        # WARNING: DRY principle breaks down in Airflow task definitions
        # ...so unfortunately we have to repeat ourself here
        prepare_airdrop = BashOperator(
            task_id="prepare_airdrop",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t prep -s airdrop -r {{ run_id }}",
            dag=dag)

        distribute = BashOperator(
            task_id="distribute",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t distrib",
            dag=dag)
        
        verify = BashOperator(
            task_id="verify",
            bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t verify",
            dag=dag)
        prepare_airdrop >> distribute >> verify

    def get_last_successful_dag_run(dag_id):
        dag_runs = DagRun.find(dag_id=POINTS_DAG_NAME, state=DagRunState.SUCCESS)
        if not dag_runs or len(dag_runs) == 0:
            # Points dag has never been run
            print(f"No previous runs of {POINTS_DAG_NAME}")
            raise ValueError(f"No successful runs found for DAG: {dag_id}")
        print(f"Found {len(dag_runs)} previous runs of {POINTS_DAG_NAME}")
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        print("Last run: ", dag_runs[0]) 
        # Query the last successful DAG run
        last_run = dag_runs[0]
        print("Last run: ", last_run)
        return last_run
    

    @task.branch(task_id="check_last_successful_points")
    def check_last_successful_points(**context) -> bool:
        try:
            pts_run = get_last_successful_dag_run(POINTS_DAG_NAME)
        except ValueError:
            return "tg_skip_weekly"
        
        prev_tokens_date = context['prev_data_interval_start_success']
        if prev_tokens_date < pts_run.end_date:
            # there has been no successful token run since the last points run
            # let's trigger weekly distribution of tokens
            # to see if any weekly tokens need to be distributed
            return "tg_all"
        return "tg_skip_weekly"

    check_last_successful_points = check_last_successful_points()

    check_last_successful_points  >> tg_all()

    check_last_successful_points  >> tg_skip_weekly()


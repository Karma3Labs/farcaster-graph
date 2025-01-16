from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator
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

POINTS_FREQUENCY_H = 1  # Define the frequency in hours
POINTS_DAG_NAME = 'update_channel_points_v2'

with DAG(
    dag_id='update_channel_tokens',
    default_args=default_args,
    description='update channel tokens started by trigger dag or manually',
    start_date=datetime(2024, 7, 10, 18),
    # schedule_interval='0 0 * * *', # every day at 00:00 UTC / 16:00 PST 
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

    skip_points_dag = EmptyOperator(task_id="skip_points_dag")

    trigger_points_dag = TriggerDagRunOperator(
        task_id='trigger_points_dag',
        trigger_dag_id=POINTS_DAG_NAME,
        execution_date='{{ macros.datetime.now() }}',
        wait_for_completion=True,
        poke_interval=60,
        conf={"trigger": "trigger_channel_points_tokens"},
    )

    @task.branch(task_id="check_last_successful_points")
    def check_last_successful_points(**context) -> bool:
        dag_runs = DagRun.find(dag_id=POINTS_DAG_NAME, state=DagRunState.SUCCESS)
        if not dag_runs or len(dag_runs) == 0:
            # No previous runs
            print(f"No previous runs of {POINTS_DAG_NAME}")
            return "trigger_main_dag"
        print(f"Found {len(dag_runs)} previous runs of {POINTS_DAG_NAME}")
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        print("Last run: ", dag_runs[0]) 
        # Query the last successful DAG run
        last_run = dag_runs[0]
        print("Last run: ", last_run)
        current_time = datetime.now(timezone.utc)
        delta = POINTS_FREQUENCY_H
        if last_run:
            print("Last run end_date: ", last_run.end_date)
            print("Last run start_date: ", last_run.start_date)
            if last_run.end_date:
                delta_last = (current_time - last_run.end_date).total_seconds() / 3600
                delta = min(delta_last, delta)
            if last_run.start_date:
                delta_last = (current_time - last_run.start_date).total_seconds() / 3600
                delta = min(delta_last, delta)
        print(f"Delta: {delta}")
        if delta >= POINTS_FREQUENCY_H:
            # Last run was more than FREQUENCY_H hours ago, so we should run
            print(f"Last run of {POINTS_DAG_NAME} was more than {POINTS_FREQUENCY_H} hours ago, so we should run")
            return "trigger_points_dag"
        return "skip_points_dag"

    check_last_successful_points = check_last_successful_points()

    check_last_successful_points >> trigger_points_dag >> tg_all()

    check_last_successful_points >> skip_points_dag >> tg_skip_weekly()


from datetime import datetime, timedelta, timezone
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.decorators import task, dag
from airflow.models import DagRun
from airflow.utils.state import DagRunState

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

FREQUENCY_H = 23  # Define the frequency in hours

@dag(
    dag_id='trigger_channel_points_tokens',
    default_args=default_args,
    description='trigger channel points and tokens dags',
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval=timedelta(hours=1), 
    # schedule=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) 
def create_trigger_dag():
    
    trigger_update_channel_tokens = TriggerDagRunOperator(
            task_id="trigger_update_channel_tokens",
            trigger_dag_id="update_channel_tokens",
            conf={"trigger": "trigger_channel_points_tokens"},
            wait_for_completion=True,
        )

    skip_points_dag = EmptyOperator(task_id="skip_points_dag")

    trigger_points_dag = TriggerDagRunOperator(
        task_id='trigger_points_dag',
        trigger_dag_id='update_channel_points_v2',
        execution_date='{{ macros.datetime.now() }}',
        conf={"trigger": "trigger_channel_points_tokens"},
    )

    @task.branch(task_id="check_last_successful_points")
    def check_last_successful_points(**context) -> bool:
        dag_runs = DagRun.find(dag_id="update_channel_points_v2", state=DagRunState.SUCCESS)
        if not dag_runs or len(dag_runs) == 0:
            # No previous runs
            print("No previous runs")
            return "trigger_main_dag"
        print(f"Found {len(dag_runs)} previous runs")
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        print("Last run: ", dag_runs[0]) 
        # Query the last successful DAG run
        last_run = dag_runs[0]
        print("Last run: ", last_run)
        current_time = datetime.now(timezone.utc)
        delta = FREQUENCY_H
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
        if delta >= FREQUENCY_H:
            # Last run was more than FREQUENCY_H hours ago, so we should run
            print(f"Last run was more than {FREQUENCY_H} hours ago, so we should run")
            return "trigger_points_dag"
        return "skip_points_dag"

    check_last_successful_points = check_last_successful_points()

    trigger_update_channel_tokens >> check_last_successful_points >> trigger_points_dag

    trigger_update_channel_tokens >> check_last_successful_points >> skip_points_dag

trigger_dag = create_trigger_dag()

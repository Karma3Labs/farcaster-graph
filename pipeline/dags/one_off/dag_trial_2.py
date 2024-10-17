from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task, dag

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

N_CHUNKS = 100  # Define the number of chunks
FREQUENCY_H = 6  # Define the frequency in hours

@task.branch(task_id="check_last_successful_run")
def check_last_successful_run(**context) -> bool:
    if context["dag_run"].external_trigger:
        # Manually triggered
        print("Manually triggered. Run now.")
        return "start_task"
    dag: DAG = context["dag"]
    # Query the last successful DAG run
    last_run = dag.get_last_dagrun(include_externally_triggered=True)
    print(last_run)
    current_time = datetime.now()
    delta = FREQUENCY_H
    if last_run and last_run.end_date:
        print("Last run: ", last_run.end_date)
        delta_last = (current_time - last_run.end_date).total_seconds() / 3600
        delta = min(delta_last, delta)
    print(f"Delta: {delta}")
    if delta >= FREQUENCY_H:
        # Last run was more than 6 hours ago, so we should run
        print("Last run was more than 6 hours ago, so we should run")
        return "start_task"
    return "end_task"

@dag(
    dag_id='one_off_dag_trial_1',
    default_args=default_args,
    description='One off dag to test new features',
    start_date=None,
    schedule_interval=timedelta(minutes=5),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False  # To avoid backfilling if not required
)
def create_dag():

    start_task = EmptyOperator(task_id="start_task")
    end_task = EmptyOperator(task_id="end_task")

    check_interval_task = check_last_successful_run()

    check_interval_task >> end_task

    check_interval_task >> start_task


dag = create_dag()

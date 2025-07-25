from datetime import datetime, timedelta, timezone

from airflow.decorators import dag, task
from airflow.models import DagRun
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.state import DagRunState

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
}

N_CHUNKS = 100  # Define the number of chunks
FREQUENCY_H = 6  # Define the frequency in hours


@dag(
    dag_id="one_off_trial_trigger_src",
    default_args=default_args,
    start_date=datetime(2024, 10, 1),
    schedule_interval=timedelta(minutes=3),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,  # To avoid backfilling if not required
)
def create_trigger_dag():
    skip_main_dag = EmptyOperator(task_id="skip_main_dag")

    trigger_main_dag = TriggerDagRunOperator(
        task_id="trigger_main_dag",
        trigger_dag_id="one_off_trial_trigger_tgt",
        execution_date="{{ macros.datetime.now() }}",
        wait_for_completion=True,
        poke_interval=60,
        conf={"trigger": "one_off_trial_trigger_src"},
    )

    def get_last_successful_dag_run(dag_id):
        dag_runs = DagRun.find(dag_id=dag_id, state=DagRunState.SUCCESS)
        if not dag_runs or len(dag_runs) == 0:
            # Given dag_id has never run before
            print(f"No previous runs of {dag_id}")
            raise ValueError(f"No successful runs found for DAG: {dag_id}")
        print(f"Found {len(dag_runs)} previous runs of {dag_id}")
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        print("Last run: ", dag_runs[0])
        # Query the last successful DAG run
        last_run = dag_runs[0]
        print("Last run: ", last_run)
        return last_run

    @task.branch(task_id="check_last_successful_run")
    def check_last_successful_run(**context) -> bool:
        try:
            last_run = get_last_successful_dag_run("one_off_trial_trigger_tgt")
        except ValueError:
            return "trigger_main_dag"
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
            return "trigger_main_dag"
        return "skip_main_dag"

    check_last_successful_run = check_last_successful_run()

    check_last_successful_run >> trigger_main_dag

    check_last_successful_run >> skip_main_dag


trigger_dag = create_trigger_dag()


@dag(
    dag_id="one_off_trial_trigger_tgt",
    default_args=default_args,
    description="One off dag to test new features",
    start_date=datetime(2024, 10, 1),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,  # To avoid backfilling if not required
)
def create_main_dag():
    start_task = EmptyOperator(task_id="start_task")

    end_task = EmptyOperator(task_id="end_task")

    start_task >> end_task


main_dag = create_main_dag()

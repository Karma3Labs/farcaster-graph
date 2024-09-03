from airflow import settings
from airflow.models import DagRun, TaskInstance
from airflow.utils.state import State

# Define your variables
dag_id = "gen_personal_graph_replica_v1"
task_id = "process_channel_chunk"
run_id = "manual__2024-07-22T06:46:15.813325+00:00"
map_index_start = 908 # 908 430
map_index_end = 939 # 939 907

# Get the session
session = settings.Session()

# Query the DagRun
dag_run = session.query(DagRun).filter(DagRun.dag_id == dag_id, DagRun.run_id == run_id).one()

# Loop through the range of map indexes and clear each task instance
for map_index in range(map_index_start, map_index_end + 1):
    try:
        # Query the TaskInstance
        task_instance = session.query(TaskInstance).filter(
            TaskInstance.dag_id == dag_id,
            TaskInstance.task_id == task_id,
            TaskInstance.run_id == run_id,
            TaskInstance.map_index == map_index
        ).one()

        # Clear the task instance
        task_instance.set_state(State.SUCCESS, session=session)
        print(f"Cleared task {task_id} with map index {map_index} for DAG {dag_id} and run ID {run_id}")
    except Exception as e:
        print(f"Could not clear task {task_id} with map index {map_index}: {e}")

# Commit the changes
session.commit()
print(f"Cleared tasks {task_id} with map indexes from {map_index_start} to {map_index_end} for DAG {dag_id} and run ID {run_id}")


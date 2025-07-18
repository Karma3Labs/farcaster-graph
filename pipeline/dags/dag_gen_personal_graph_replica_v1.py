import base64
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.decorators import task
from airflow.operators.python import get_current_context
from airflow.utils.trigger_rule import TriggerRule
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=5),
    # 'on_success_callback':[cleanup_function],
    # 'on_failure_callback':[cleanup_function],
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}


@task
def extract_fids(raw_log: str) -> list[str]:
    lines_str = base64.b64decode(raw_log).decode("utf-8")
    lines = lines_str.split("\n")
    chunks_of_fids_str = lines[-2]

    # Returns JSON object as a dictionary
    chunks_of_fids = json.loads(chunks_of_fids_str)
    print(f"len={len(chunks_of_fids)} each_len={len(chunks_of_fids[0])} ")

    chunks_of_str_fids = [",".join(map(str, chunk)) for chunk in chunks_of_fids]
    return chunks_of_str_fids


with DAG(
    dag_id="gen_personal_graph_replica_v1",
    default_args=default_args,
    description="Every hour, try running personal graph script on eigen7 replica. Script has internal check for 36 hours",
    start_date=datetime(2024, 7, 24),
    # schedule_interval='0 0 */2 * *',
    schedule_interval=timedelta(days=7),
    max_active_runs=1,
    is_paused_upon_creation=True,
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id="eigen7", keepalive_interval=60)

    eigen7_graph_reload = SSHOperator(
        task_id="eigen7_graph_reload_v1",
        command="cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t graph_reload -r {{ run_id }}",
        ssh_hook=ssh_hook,
        cmd_timeout=600,  # average is 4.5mins
        dag=dag,
    )

    eigen7_fetch_fids = SSHOperator(
        task_id="eigen7_fetch_fids_v1",
        command="cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t fetch_fids -r {{ run_id }}",
        ssh_hook=ssh_hook,
        cmd_timeout=180,  # average is 30secs
        dag=dag,
        do_xcom_push=True,  # ssh command output is pushed to xcom ie., fid[][] in stdout
    )

    @task(max_active_tis_per_dagrun=30)
    def process_personal_chunk(chunk: str):
        context = get_current_context()
        map_index = context["ti"].map_index
        run_id = context["run_id"]

        process_task = SSHOperator(
            task_id=f"eigen7_gen_personal_chunk_v1_{map_index}",  # Use the map index for a unique task_id
            command=f"cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t generate -f {chunk} -r {run_id} -m {map_index}",
            ssh_hook=ssh_hook,
            cmd_timeout=None,
            dag=dag,
        )
        process_task.execute(context)

    extract_fids_task = extract_fids(eigen7_fetch_fids.output)

    # Create dynamic tasks
    process_tasks = process_personal_chunk.expand(chunk=extract_fids_task)

    eigen7_consolidate = SSHOperator(
        task_id="eigen7_consolidate_v1",
        command="cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t consolidate -r {{ run_id }}",
        ssh_hook=ssh_hook,
        cmd_timeout=900,  # average is 3.5mins but be lenient since this is the last task in DAG
        dag=dag,
        priority_weight=42,
    )

    (
        eigen7_graph_reload
        >> eigen7_fetch_fids
        >> extract_fids_task
        >> process_tasks
        >> eigen7_consolidate
    )

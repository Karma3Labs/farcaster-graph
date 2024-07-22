from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.hooks.ssh_hook import SSHHook

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

import json

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

@task
def extract_fids(chunks_of_fids_str: str) -> list[list[int]]:
    import json
    chunks_of_fids = json.loads(chunks_of_fids_str)
    print(f'len={chunks_of_fids} each_len={len(chunks_of_fids[0])} fids[0]={chunks_of_fids[0]} fids[{len(chunks_of_fids[0]) -1}]={chunks_of_fids[:-1]} ')

    return chunks_of_fids

with DAG(
    dag_id='gen_personal_graph_replica_v1',
    default_args=default_args,
    description='Every hour, try running personal graph script on eigen7 replica. Script has internal check for 36 hours',
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval='0 * * * *',
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id='eigen7', keepalive_interval=60, cmd_timeout=None)

    eigen7_graph_reload = SSHOperator(
        task_id="eigen7_graph_reload_v1",
        command=f"cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t graph_reload",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_fetch_fids = SSHOperator(
        task_id="eigen7_fetch_fids_v1",
        command=f"cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t fetch_fids",
        ssh_hook=ssh_hook,
        dag=dag,
        do_xcom_push=True,
    )

    @task(max_active_tis_per_dagrun=18)
    def process_channel_chunk(chunk: list):
        chunk_str = ','.join(chunk)

        process_task = SSHOperator(
            task_id=f'eigen7_gen_personal_chunk_v1_{hash(chunk_str)}',
            command=f"cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline_v1.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -t generate -f {chunk_str}",
            env={'PYTHONUNBUFFERED': '1'},  # Ensures real-time logging
            ssh_hook=ssh_hook,
            dag=dag,
        )
        process_task.execute({})

    extract_fids_task = extract_fids(eigen7_fetch_fids.output)

    # Create dynamic tasks
    process_tasks = process_channel_chunk.expand(chunk=extract_fids_task)

    eigen7_graph_reload >> eigen7_fetch_fids >> extract_fids_task >> process_tasks
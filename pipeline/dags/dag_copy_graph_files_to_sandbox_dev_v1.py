from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.providers.ssh.operators.ssh import SSHHook
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.sensors.external_task import ExternalTaskSensor

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

sandbox_dev_host = Variable.get("sandbox_dev_host")
sandbox_dev_ssh_cred_path = Variable.get("sandbox_dev_ssh_cred_path")

with DAG(
    dag_id="copy_graph_files_to_sandbox_dev_v1",
    default_args=default_args,
    description="re-generate graph for farcaster-graph API server. copy re-generated all graph files to dev sandbox from eigen2",
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval="0 0 * * *",
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    ssh_hook = SSHHook(ssh_conn_id='eigen6', keepalive_interval=60, cmd_timeout=None)

    run_graph_pipeline = BashOperator(
        task_id="run_graph_pipeline",
        bash_command="cd /pipeline; ./run_graph_pipeline.sh -w . -i tmp/graph_files/ -o tmp/graph_files/ -v ./.venv ",
        dag=dag,
    )

    dev_copy_all_pkl_files = SSHOperator(
        task_id="dev_copy_all_pkl_files",
        command=f"scp -v -i {sandbox_dev_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*.pkl ubuntu@{sandbox_dev_host}:/data/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    dev_copy_success_pkl_files = SSHOperator(
        task_id="dev_copy_success_pkl_files",
        command=f"scp -v -i {sandbox_dev_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*_SUCCESS ubuntu@{sandbox_dev_host}:/data/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )



    run_graph_pipeline >> dev_copy_all_pkl_files >> dev_copy_success_pkl_files
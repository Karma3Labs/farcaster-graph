from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.providers.ssh.operators.ssh import SSHHook, SSHOperator
from airflow.sensors.external_task import ExternalTaskSensor
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

dev_sandbox_pipeline_path = Variable.get("dev_sandbox_pipeline_path")
data_backup_s3_bucket = Variable.get("data_backup_s3_bucket")

with DAG(
    dag_id="copy_graph_files_to_sandbox_dev_v2",
    default_args=default_args,
    description="re-generate graph for farcaster-graph API server. copy re-generated all graph files to dev sandbox from backup s3",
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval="0 0 * * *",
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    ssh_hook = SSHHook(
        ssh_conn_id="sandbox_staging", keepalive_interval=60, cmd_timeout=None
    )

    download_pqt_file = SSHOperator(
        task_id="download_pqt_file_v1",
        command=f"cd {dev_sandbox_pipeline_path}; ./run_graph_pipeline.sh -o /data/serve_files -s {data_backup_s3_bucket} ",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    download_pqt_file

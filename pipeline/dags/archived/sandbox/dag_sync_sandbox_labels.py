from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

sandbox_db_sync_path = Variable.get("sandbox_db_sync_path")
dev_sandbox_db_sync_path = Variable.get("dev_sandbox_db_sync_path")

with DAG(
    dag_id="sync_sandbox_db_labels",
    default_args=default_args,
    description="sync labels to the sandbox",
    start_date=datetime(2024, 7, 10, 18),
    # schedule_interval='*/10 * * * *',
    schedule=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id="eigen2", keepalive_interval=60, cmd_timeout=None)

    run_append = SSHOperator(
        task_id="run_append_v1",
        command=f"cd {sandbox_db_sync_path}; ./1-run-append_v1.sh -l",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    run_append

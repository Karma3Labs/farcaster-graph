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

dev_sandbox_db_sync_path = Variable.get("dev_sandbox_db_sync_path")

with DAG(
    dag_id="dag_sync_sandbox_db_dev_v0",
    default_args=default_args,
    description="sync the db table of the sandboxed read replica",
    start_date=datetime(2024, 7, 10, 18),
    # schedule_interval='*/10 * * * *',
    schedule_interval=None,
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id="eigen2", keepalive_interval=60, cmd_timeout=None)

    run_append_dev = SSHOperator(
        task_id="run_append_dev_v0",
        command=f"cd {dev_sandbox_db_sync_path}; ./1-run-append.sh -d 5 ",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    run_remove_dev = SSHOperator(
        task_id="run_remove_dev_v0",
        command=f"cd {dev_sandbox_db_sync_path}; ./2-run-remove.sh ",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    run_append_dev >> run_remove_dev

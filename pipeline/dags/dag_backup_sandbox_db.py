from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.hooks.ssh_hook import SSHHook

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

sandbox_db_sync_path = Variable.get("sandbox_db_sync_path")
dev_sandbox_db_sync_path = Variable.get("dev_sandbox_db_sync_path")

with DAG(
    dag_id='dag_backup_sandbox_db_v0',
    default_args=default_args,
    description='sync the db table of the sandboxed read replica',
    start_date=datetime(2024, 8, 10, 18),
    schedule_interval='0 0 * * 0,3', # backup every Sunday and Wednesday
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id='eigen2', keepalive_interval=60, cmd_timeout=None)

    run_sandbox_backup = SSHOperator(
        task_id="run_sandbox_backup_v0",
        command=f"cd {sandbox_db_sync_path}; ./run-backup.sh ",
        ssh_hook=ssh_hook,
        dag=dag)

    run_sandbox_backup

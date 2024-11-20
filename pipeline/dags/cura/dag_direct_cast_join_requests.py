from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.providers.ssh.operators.ssh import SSHHook
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.decorators import task_group

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id="cura_direct_cast_join_requests",
    default_args=default_args,
    description="Direct cast join requests from curabot",
    start_date=datetime(2024, 11, 7),
    schedule_interval='*/5 * * * *',
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    ssh_hook = SSHHook(ssh_conn_id='eigen1', keepalive_interval=60, cmd_timeout=None)

    eigen1_install_dependencies = SSHOperator(
        task_id="cura_eigen1_install_deps",
        command=f"cd cura-bot && git reset --hard HEAD && git pull origin main && pnpm i",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen1_direct_cast_join_requests = SSHOperator(
        task_id="cura_eigen1_direct_cast_join_requests",
        command=f"cd cura-bot && npm run script:direct_cast_join_requests",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen1_install_dependencies >> eigen1_direct_cast_join_requests


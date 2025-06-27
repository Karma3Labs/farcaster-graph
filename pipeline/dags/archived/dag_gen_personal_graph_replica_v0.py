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

with DAG(
    dag_id="gen_personal_graph_replica_v0",
    default_args=default_args,
    description="Every hour, try running personal graph script on eigen7 replica. Script has internal check for 36 hours",
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval='0 * * * *',
    schedule_interval=None,
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id="eigen7", keepalive_interval=60, cmd_timeout=None)

    eigen7_copy_localtrust_csv_files = SSHOperator(
        task_id="eigen7_gen_personal_graph",
        command=f"cd ~/farcaster-graph/pipeline; ./run_personal_graph_pipeline.sh -i ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv -o ~/wip_files/ -w . -v .venv -s k3l-openrank-farcaster -l /var/log/farcaster-graph/ ",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_copy_localtrust_csv_files

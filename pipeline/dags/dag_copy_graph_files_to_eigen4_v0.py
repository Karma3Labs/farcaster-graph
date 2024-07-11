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
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

eigen4_hostname = Variable.get("eigen4_hostname")
eigen4_username = Variable.get("eigen4_username")

eigen2_ssh_cred_path = Variable.get('eigen2_ssh_cred_path')

with DAG(
    dag_id='dag_copy_graph_files_to_eigen4_v0',
    default_args=default_args,
    description='re-generate graph for farcaster-graph API server. copy re-generated graph files to eigen4 from eigen2',
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval='20 1-23/6 * * *',
    catchup=False,
) as dag:
    ssh_hook = SSHHook(ssh_conn_id='eigen2', keepalive_interval=60, cmd_timeout=None)

    run_graph_pipeline_remote = SSHOperator(
        task_id="run_graph_pipeline_remote_v0",
        command= "cd ~/farcaster-graph/pipeline; ./run_graph_pipeline.sh -w . -o ~/serve_files -v ./.venv ",
        ssh_hook=ssh_hook,
        dag=dag)

    copy_all_pkl_files = SSHOperator(
        task_id="copy_all_pkl_v0",
        command=f"scp -v -i {eigen2_ssh_cred_path} ~/serve_files/fc_*.pkl {eigen4_username}@{eigen4_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    copy_success_pkl_files = SSHOperator(
        task_id="copy_success_pkl_v0",
        command=f"scp -v -i {eigen2_ssh_cred_path} ~/serve_files/fc_*_SUCCESS {eigen4_username}@{eigen4_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    run_graph_pipeline_remote >> copy_all_pkl_files >> copy_success_pkl_files

# a hook can also be defined directly in the code:
# sshHook = SSHHook(remote_host='server.com', username='admin', key_file='/opt/airflow/keys/ssh.key')


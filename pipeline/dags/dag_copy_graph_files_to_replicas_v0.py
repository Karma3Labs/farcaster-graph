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

eigen4_hostname = Variable.get("eigen4_hostname")
eigen4_username = Variable.get("eigen4_username")
eigen4_ssh_cred_path = Variable.get('eigen4_ssh_cred_path')

eigen7_hostname = Variable.get("eigen7_hostname")
eigen7_username = Variable.get("eigen7_username")
eigen7_ssh_cred_path = Variable.get('eigen7_ssh_cred_path')

with DAG(
    dag_id='dag_copy_graph_files_to_replicas_v0',
    default_args=default_args,
    description='re-generate graph for farcaster-graph API server. copy re-generated all graph files to eigen4 and eigen7 from eigen2',
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

    eigen4_copy_all_pkl_files = SSHOperator(
        task_id="eigen4_copy_all_pkl_v0",
        command=f"scp -v -i {eigen4_ssh_cred_path} ~/serve_files/fc_*.pkl {eigen4_username}@{eigen4_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    eigen4_copy_success_pkl_files = SSHOperator(
        task_id="eigen4_copy_success_pkl_v0",
        command=f"scp -v -i {eigen4_ssh_cred_path} ~/serve_files/fc_*_SUCCESS {eigen4_username}@{eigen4_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    eigen7_copy_personal_pkl_files = SSHOperator(
        task_id="eigen7_copy_personal_pkl_v0",
        command=f"scp -v -i {eigen7_ssh_cred_path} ~/serve_files/fc_engagement_fid_ig.pkl {eigen7_username}@{eigen7_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    eigen7_copy_localtrust_csv_files = SSHOperator(
        task_id="eigen7_copy_localtrust_csv_v0",
        command=f"scp -v -i {eigen7_ssh_cred_path} ~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv {eigen7_username}@{eigen7_hostname}:~/serve_files",
        ssh_hook=ssh_hook,
        dag=dag)

    run_graph_pipeline_remote >> eigen4_copy_all_pkl_files >> eigen4_copy_success_pkl_files
    run_graph_pipeline_remote >> [eigen7_copy_personal_pkl_files, eigen7_copy_localtrust_csv_files]

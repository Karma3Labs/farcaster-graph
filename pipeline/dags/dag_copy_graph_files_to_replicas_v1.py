from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.ssh.hooks.ssh import SSHHook

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

eigen2_ipv4 = Variable.get("eigen2_ipv4")
eigen4_ipv4 = Variable.get("eigen4_ipv4")
eigen7_ipv4 = Variable.get("eigen7_ipv4")
eigen5_ssh_cred_path = Variable.get("eigen5_ssh_cred_path")

with DAG(
    dag_id="dag_copy_graph_files_to_replicas_v1",
    default_args=default_args,
    description="re-generate graph for farcaster-graph API server. copy re-generated all graph files to eigen4 and eigen7 from eigen2",
    start_date=datetime(2024, 8, 19),
    schedule_interval="20 1-23/6 * * *",
    catchup=False,
) as dag:
    
    # TODO need to refactor this dag to execute on Eigen6 and use BashOperator
    ssh_hook = SSHHook(ssh_conn_id="eigen5", keepalive_interval=60, cmd_timeout=None)

    run_graph_pipeline = SSHOperator(
        task_id="run_graph_pipeline_v0",
        command="cd ~/farcaster-graph/pipeline; ./run_graph_pipeline.sh -w . -i ~/graph_files -o ~/graph_files -v ./.venv ",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen2_copy_all_pkl_files = SSHOperator(
        task_id="eigen2_copy_all_pkl_v0",
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/fc_*.pkl ubuntu@{eigen2_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen2_copy_success_pkl_files = SSHOperator(
        task_id="eigen2_copy_success_pkl_v0",
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/fc_*_SUCCESS ubuntu@{eigen2_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen4_copy_all_pkl_files = SSHOperator(
        task_id="eigen4_copy_all_pkl_v0",
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/fc_*.pkl ubuntu@{eigen4_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen4_copy_success_pkl_files = SSHOperator(
        task_id="eigen4_copy_success_pkl_v0",
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/fc_*_SUCCESS ubuntu@{eigen4_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_copy_personal_pkl_files = SSHOperator(
        task_id="eigen7_copy_personal_pkl_v0",
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/fc_engagement_fid_ig.pkl ubuntu@{eigen7_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_copy_localtrust_csv_files = SSHOperator(
        task_id="eigen7_copy_localtrust_csv_v0",
        # TODO stop renaming to lt_l1rep6rec3m12enhancedConnections_fid.csv and just call it engagement
        bash_command=f"scp -v -i {eigen5_ssh_cred_path} ~/graph_files/localtrust.engagement.csv ubuntu@{eigen7_ipv4}:~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    run_graph_pipeline >> eigen2_copy_all_pkl_files >> eigen2_copy_success_pkl_files
    run_graph_pipeline >> eigen4_copy_all_pkl_files >> eigen4_copy_success_pkl_files
    run_graph_pipeline >> [
        eigen7_copy_personal_pkl_files,
        eigen7_copy_localtrust_csv_files,
    ]

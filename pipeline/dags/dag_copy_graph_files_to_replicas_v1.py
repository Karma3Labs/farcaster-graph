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

eigen2_ipv4 = Variable.get("eigen2_ipv4")
eigen4_ipv4 = Variable.get("eigen4_ipv4")
eigen7_ipv4 = Variable.get("eigen7_ipv4")
eigen6_ssh_cred_path = Variable.get("eigen6_ssh_cred_path")

with DAG(
    dag_id="dag_copy_graph_files_to_replicas_v1",
    default_args=default_args,
    description="re-generate graph for farcaster-graph API server. copy re-generated all graph files to eigen4 and eigen7 from eigen2",
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval="20 1-23/6 * * *",
    catchup=False,
) as dag:

    # TODO change this to TriggerDagRunOperator
    check_upstream = ExternalTaskSensor(
        task_id="check_upstream",
        external_dag_id="gen_globaltrust_v1",
        external_task_id="rmdir_tmp",
        allowed_states=["success"],
        failed_states=["failed", "skipped"],
    )

    ssh_hook = SSHHook(ssh_conn_id='eigen6', keepalive_interval=60, cmd_timeout=None)
 
    run_graph_pipeline = BashOperator(
        task_id="run_graph_pipeline",
        bash_command="cd /pipeline; ./run_graph_pipeline.sh -w . -i tmp/graph_files/ -o tmp/graph_files/ -v ./.venv ",
        dag=dag,
    )

    eigen2_copy_all_pkl_files = SSHOperator(
        task_id="eigen2_copy_all_pkl_files",
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*.pkl ubuntu@{eigen2_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen2_copy_success_pkl_files = SSHOperator(
        task_id="eigen2_copy_success_pkl_files",
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*_SUCCESS ubuntu@{eigen2_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen4_copy_all_pkl_files = SSHOperator(
        task_id="eigen4_copy_all_pkl_files",
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*.pkl ubuntu@{eigen4_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen4_copy_success_pkl_files = SSHOperator(
        task_id="eigen4_copy_success_pkl_files",
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*_SUCCESS ubuntu@{eigen4_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_copy_personal_pkl_files = SSHOperator(
        task_id="eigen7_copy_personal_pkl_files",
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_engagement_fid_ig.pkl ubuntu@{eigen7_ipv4}:~/serve_files/",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    eigen7_copy_localtrust_csv_files = SSHOperator(
        task_id="eigen7_copy_localtrust_csv_files",
        # TODO stop renaming to lt_l1rep6rec3m12enhancedConnections_fid.csv and just call it engagement
        command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/localtrust.engagement.csv ubuntu@{eigen7_ipv4}:~/serve_files/lt_l1rep6rec3m12enhancedConnections_fid.csv",
        ssh_hook=ssh_hook,
        dag=dag,
    )

    check_upstream >> run_graph_pipeline >> eigen2_copy_all_pkl_files >> eigen2_copy_success_pkl_files
    check_upstream >> run_graph_pipeline >> eigen4_copy_all_pkl_files >> eigen4_copy_success_pkl_files
    check_upstream >> run_graph_pipeline >> [
        eigen7_copy_personal_pkl_files,
        eigen7_copy_localtrust_csv_files,
    ]

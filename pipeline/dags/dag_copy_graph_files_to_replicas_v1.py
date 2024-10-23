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

eigen4_ipv4 = Variable.get("eigen4_ipv4")
eigen5_ipv4 = Variable.get("eigen5_ipv4")
eigen7_ipv4 = Variable.get("eigen7_ipv4")
eigen6_ssh_cred_path = Variable.get("eigen6_ssh_cred_path")

with DAG(
    dag_id="copy_graph_files_to_replicas_v1",
    default_args=default_args,
    description="re-generate graph for farcaster-graph API server. copy re-generated all graph files to eigen4 and eigen7 from eigen2",
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval="20 1-23/6 * * *",
    schedule=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    ssh_hook = SSHHook(ssh_conn_id='eigen6', keepalive_interval=60, cmd_timeout=None)

    @task_group(group_id="gen_graphs")
    def tg_gen_graphs():
        gen_following_graph = BashOperator(
            task_id="gen_following_graph",
            bash_command="cd /pipeline; ./run_graph_pipeline.sh -w . -v ./.venv"
                            " -i tmp/graph_files/localtrust.following.csv -o tmp/graph_files/ -p fc_following_fid ",
            dag=dag,
        )

        gen_engagement_graph = BashOperator(
            task_id="gen_engagement_graph",
            bash_command="cd /pipeline; ./run_graph_pipeline.sh -w . -v ./.venv"
                            " -i tmp/graph_files/localtrust.engagement.csv -o tmp/graph_files/ -p fc_engagement_fid ",
            dag=dag,
        )

        gen_90day_graph = BashOperator(
            task_id="gen_90day_graph",
            bash_command="cd /pipeline; ./run_graph_pipeline.sh -w . -v ./.venv"
                            " -i tmp/graph_files/localtrust.graph_90dv3.csv -o tmp/graph_files/ -p fc_90dv3_fid ",
            dag=dag,
        )

        gen_following_graph >> gen_engagement_graph >> gen_90day_graph

    # end tg_gen_graphs

    @task_group(group_id="copy_graphs")
    def tg_copy_graphs():

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

        eigen5_copy_all_pkl_files = SSHOperator(
            task_id="eigen5_copy_all_pkl_files",
            command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*.pkl ubuntu@{eigen5_ipv4}:~/serve_files/",
            ssh_hook=ssh_hook,
            dag=dag,
        )

        eigen5_copy_success_pkl_files = SSHOperator(
            task_id="eigen5_copy_success_pkl_files",
            command=f"scp -v -i {eigen6_ssh_cred_path} ~/farcaster-graph/pipeline/tmp/graph_files/fc_*_SUCCESS ubuntu@{eigen5_ipv4}:~/serve_files/",
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

        eigen4_copy_all_pkl_files >> eigen4_copy_success_pkl_files
        eigen5_copy_all_pkl_files >> eigen5_copy_success_pkl_files
        eigen7_copy_personal_pkl_files
        eigen7_copy_localtrust_csv_files

    # end tg_copy_graphs

    tg_gen_graphs() >> tg_copy_graphs()

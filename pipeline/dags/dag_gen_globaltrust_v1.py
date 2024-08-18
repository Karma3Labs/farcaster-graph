from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.ssh.hooks.ssh import SSHHook
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty


default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='gen_globaltrust_v1',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 8, 16),
    schedule_interval='0 */6 * * *',
    catchup=False,
) as dag:

    ssh_hook = SSHHook(ssh_conn_id='eigen5', keepalive_interval=60, cmd_timeout=None)

    mkdir_tmp =  SSHOperator(
        task_id="mkdir_tmp",
        command= "cd ~/farcaster-graph/pipeline; mkdir -p tmp/{{ run_id }}",
        ssh_hook=ssh_hook,
        dag=dag)

    gen_globaltrust = SSHOperator(
        task_id="gen_localtrust",
        command= "cd ~/farcaster-graph/pipeline; ./run_globaltrust_pipeline.sh -s localtrust -w . -v ./.venv -t tmp/{{ run_id }} -o ~/graph_files/",
        ssh_hook=ssh_hook,
        dag=dag)
    
    gen_globaltrust = SSHOperator(
        task_id="compute_globaltrust",
        command= "cd ~/farcaster-graph/pipeline; ./run_globaltrust_pipeline.sh -s compute -w . -v ./.venv -t tmp/{{ run_id }} -o ~/graph_files/",
        ssh_hook=ssh_hook,
        dag=dag)
    
    upload_to_dune =  SSHOperator(
        task_id="insert_globaltrust_to_dune_v3",
        command= "cd ~/farcaster-graph/pipeline/dags/pg_to_dune; ./upload_to_dune.sh insert_globaltrust_to_dune_v3",
        ssh_hook=ssh_hook,
        dag=dag)
    
    rmdir_tmp =  SSHOperator(
        task_id="rmdir_tmp",
        command= "cd ~/farcaster-graph/pipeline; rm -rf tmp/{{ run_id }}",
        ssh_hook=ssh_hook,
        trigger_rule=TriggerRule.ONE_SUCCESS,
        dag=dag)

    mkdir_tmp >> gen_globaltrust >> upload_to_dune >> rmdir_tmp.as_teardown(setups=mkdir_tmp)

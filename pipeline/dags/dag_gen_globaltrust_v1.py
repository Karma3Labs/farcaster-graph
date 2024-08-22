from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.bash import BashOperator

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
    is_paused_upon_creation=True,
    catchup=False,
) as dag:

    mkdir_tmp =  BashOperator(
        task_id="mkdir_tmp",
        bash_command= "cd /pipeline; mkdir -p tmp/{{ run_id }}; mkdir -p tmp/graph_files",
        dag=dag)

    prep_globaltrust = BashOperator(
        task_id="prep_globaltrust",
        bash_command= "cd /pipeline; ./run_globaltrust_pipeline.sh -s prep -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/",
        dag=dag)
    
    compute_globaltrust = BashOperator(
        task_id="compute_globaltrust",
        bash_command= "cd /pipeline; ./run_globaltrust_pipeline.sh -s compute -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/",
        dag=dag)
    
    upload_to_dune =  BashOperator(
        task_id="insert_globaltrust_to_dune_v3",
        bash_command= "cd /pipeline/dags/pg_to_dune; ./upload_to_dune.sh insert_globaltrust_to_dune_v3",
        dag=dag)
    
    rmdir_tmp =  BashOperator(
        task_id="rmdir_tmp",
        bash_command= "cd /pipeline; rm -rf tmp/{{ run_id }}",
        trigger_rule=TriggerRule.ONE_SUCCESS,
        dag=dag)

    mkdir_tmp >> prep_globaltrust >> compute_globaltrust >> upload_to_dune >> rmdir_tmp.as_teardown(setups=mkdir_tmp)

from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
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
    dag_id='one_off_gen_localtrust',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 8, 16),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    mkdir_tmp =  BashOperator(
        task_id="mkdir_tmp",
        bash_command= "cd /pipeline; mkdir -p tmp/one_off_graph_files",
        dag=dag)

    prep_globaltrust = BashOperator(
        task_id="prep_globaltrust",
        bash_command= "cd /pipeline; ./run_globaltrust_pipeline.sh -s prep -w . -v ./.venv -t tmp/one_off_graph_files -o tmp/one_off_graph_files/",
        dag=dag)
    
    push_to_s3 = BashOperator(
        task_id='backup_localtrust',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh localtrust_v1 /pipeline/tmp/one_off_graph_files"
    )

    rmdir_tmp =  BashOperator(
        task_id="rmdir_tmp",
        bash_command= "cd /pipeline; rm -rf tmp/{{ run_id }}",
        trigger_rule=TriggerRule.ONE_SUCCESS,
        dag=dag)

    # TODO do we need to backup every 6 hours ? Revisit this later.
    # trigger_backup = TriggerDagRunOperator(
    #     task_id="trigger_backup",
    #     trigger_dag_id="backup_to_s3_v1",
    #     conf={"trigger": "gen_globaltrust_v1"},
    # )

    (
        mkdir_tmp
        >> prep_globaltrust
        >> push_to_s3
        >> rmdir_tmp.as_teardown(setups=mkdir_tmp)
    )

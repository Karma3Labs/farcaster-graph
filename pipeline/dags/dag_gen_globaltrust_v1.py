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
    dag_id='gen_globaltrust_v1',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 8, 16),
    # schedule_interval='0 */6 * * *',
    schedule_interval=timedelta(hours=6),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    mkdir_tmp =  BashOperator(
        task_id="mkdir_tmp",
        bash_command= "cd /pipeline; mkdir -p tmp/{{ run_id }}; mkdir -p tmp/graph_files",
        dag=dag)

    prep_globaltrust = BashOperator(
        task_id="prep_globaltrust",
        bash_command= "cd /pipeline; ./run_globaltrust_pipeline.sh -s prep"
                        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/",
        dag=dag)
    
    gen_90day_graph = BashOperator(
        task_id="gen_90day_localtrust",
        bash_command="cd /pipeline; ./run_globaltrust_pipeline.sh -s graph"
                        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/ -d {{ macros.ds_add(ds, -90) }}",
        dag=dag,
    )

    compute_globaltrust = BashOperator(
        task_id="compute_globaltrust",
        bash_command= "cd /pipeline; ./run_globaltrust_pipeline.sh -s compute"
                        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/",
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

    trigger_copy_to_replica = TriggerDagRunOperator(
        task_id="trigger_copy_to_replica",
        trigger_dag_id="copy_graph_files_to_replicas_v1",
        conf={"trigger": "gen_globaltrust_v1"},
    )

    trigger_refresh_views = TriggerDagRunOperator(
        task_id="trigger_refresh_views",
        trigger_dag_id="refresh_rank_view_v0",
        conf={"trigger": "gen_globaltrust_v1"},
    )

    trigger_sync_sandbox = TriggerDagRunOperator(
        task_id="trigger_sync_sandbox",
        trigger_dag_id="sync_sandbox_db_ranks",
        conf={"trigger": "gen_globaltrust_v1"},
    )
    # TODO do we need to backup every 6 hours ? Revisit this later.
    # trigger_backup = TriggerDagRunOperator(
    #     task_id="trigger_backup",
    #     trigger_dag_id="backup_to_s3_v1",
    #     conf={"trigger": "gen_globaltrust_v1"},
    # )

    (
        mkdir_tmp
        >> prep_globaltrust
        >> gen_90day_graph
        >> compute_globaltrust
        >> upload_to_dune
        >> trigger_refresh_views
        >> trigger_copy_to_replica
        >> trigger_sync_sandbox
        >> rmdir_tmp.as_teardown(setups=mkdir_tmp)
    )

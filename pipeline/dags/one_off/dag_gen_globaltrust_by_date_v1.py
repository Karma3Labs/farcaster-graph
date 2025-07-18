from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.trigger_rule import TriggerRule
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id="one_off_gen_globaltrust_by_date_v1",
    default_args=default_args,
    description="This runs run_globaltrust_pipeline.sh without any optimization",
    start_date=datetime(2024, 8, 16),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    mkdir_tmp = BashOperator(
        task_id="mkdir_tmp",
        bash_command="cd /pipeline; mkdir -p tmp/{{ run_id }}; mkdir -p tmp/graph_files",
        dag=dag,
    )

    prep_globaltrust = BashOperator(
        task_id="prep_globaltrust",
        bash_command="cd /pipeline; ./run_globaltrust_pipeline.sh -s prep"
        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/ -d 2024-10-26",
        dag=dag,
    )

    compute_engagement = BashOperator(
        task_id="compute_engagement",
        bash_command="cd /pipeline; ./run_globaltrust_pipeline.sh -s compute_engagement"
        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/ -d 2024-10-26",
        dag=dag,
    )

    insert_db = BashOperator(
        task_id="insert_db",
        bash_command="cd /pipeline; ./run_globaltrust_pipeline.sh -s insert_db"
        " -w . -v ./.venv -t tmp/{{ run_id }} -o tmp/graph_files/ -d 2024-10-26",
        dag=dag,
    )

    upload_to_dune = BashOperator(
        task_id="upload_to_dune",
        bash_command="cd /pipeline/dags/pg_to_dune; ./upload_to_dune.sh overwrite_globaltrust_in_dune_v3",
        dag=dag,
    )

    trigger_refresh_views = TriggerDagRunOperator(
        task_id="trigger_refresh_views",
        trigger_dag_id="refresh_rank_view_v0",
        conf={"trigger": "gen_globaltrust_v1"},
    )

    # trigger_sync_sandbox = TriggerDagRunOperator(
    #     task_id="trigger_sync_sandbox",
    #     trigger_dag_id="sync_sandbox_globaltrust",
    #     conf={"trigger": "gen_globaltrust_v1"},
    # )

    (
        mkdir_tmp
        >> prep_globaltrust
        >> compute_engagement
        >> insert_db
        >> upload_to_dune
        >> trigger_refresh_views
        # >> trigger_sync_sandbox
    )

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='run_cast_pipeline_v0',
    default_args=default_args,
    description='extract cast interactions and refresh pg statistics',
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval='*/10 * * * *',
    schedule_interval=timedelta(minutes=10),
    max_active_runs=1,
    is_paused_upon_creation=True,
    catchup=False,
) as dag:
    
    insert = BashOperator(
        task_id='insert_cast_actions',
        bash_command='cd /pipeline/ && ./run_cast_pipeline.sh -v ./.venv/ '
    )

    insert8 = BashOperator(
        task_id='insert_cast_actions_e8',
        bash_command='cd /pipeline/ && ./run_cast_pipeline.sh -v ./.venv/ -p eigen8 '
    )

    refresh = BashOperator(
        task_id='refresh_parent_casts_view',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_recent_parent_casts;"
        '''
    )

    refresh8 = BashOperator(
        task_id='refresh_parent_casts_view_e8',
        bash_command='''cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
        REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_recent_parent_casts;"
        '''
    )

    # vacuum = BashOperator(
    #     task_id='vacuum_k3l_recent_parent_casts_v0',
    #     bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
    #     VACUUM ANALYZE k3l_recent_parent_casts;"
    #     '''
    # )

    # vacuum8 = BashOperator(
    #     task_id='vacuum_k3l_recent_parent_casts_v0_e8',
    #     bash_command='''cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
    #     VACUUM ANALYZE k3l_recent_parent_casts;"
    #     '''
    # )

    insert >> refresh 
    insert8 >> refresh8

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
    schedule_interval='*/10 * * * *',
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id='run_cast_pipeline_v0',
        bash_command='cd /pipeline/ && ./run_cast_pipeline.sh -v ./.venv/ '
    )

    task2 = BashOperator(
        task_id='analyze_k3l_cast_action_v0',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        ANALYZE k3l_cast_action;"
        '''
    )

    task3 = BashOperator(
        task_id='refresh_k3l_recent_parent_casts_v0',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_recent_parent_casts;"
        '''
    )

    task4 = BashOperator(
        task_id='vacuum_k3l_recent_parent_casts_v0',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        VACUUM ANALYZE k3l_recent_parent_casts;"
        '''
    )

    task1 >> task2 >> task3 >> task4

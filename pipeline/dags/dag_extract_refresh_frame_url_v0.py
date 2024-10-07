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
    dag_id='extract_frame_url_v0',
    default_args=default_args,
    description='Extract urls from cast embeds for frames and refresh pg statistics',
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval='1-59/20 * * * *',
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id='run_urlextract_pipeline',
        bash_command='cd /pipeline/ && ./run_urlextract_pipeline.sh -w . '
    )

    task2 = BashOperator(
        task_id='run_frame_scraper',
        bash_command='cd /pipeline/ && ./run_frame_scraper.sh -v ./.venv/ '
    )

    task3 = BashOperator(
        task_id='analyze_url_labels_and_mapping',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        ANALYZE k3l_url_labels; ANALYZE k3l_cast_embed_url_mapping;"
        '''
    )

    task4 = BashOperator(
        task_id='refresh_k3l_frame_interaction',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_frame_interaction;"
        '''
    )

    task5 = BashOperator(
        task_id='vacuum_k3l_frame_interaction',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        VACUUM ANALYZE k3l_frame_interaction;"
        '''
    )

    task1 >> task2 >> task3 >> task4 >> task5

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.decorators import task, dag
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

import math
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

PIPELINE_DIR = './'
VENV_DIR = './.venv'
SHELL_SCRIPT = f'{PIPELINE_DIR}/run_channel_scraper_v3.sh'
CSV_PATH = f'{PIPELINE_DIR}/channels/Top_Channels.csv'
N_CHUNKS = 100  # Define the number of chunks

@task
def extract_channel_ids(channel_ids: str) -> list:
    channel_ids_list = channel_ids.split(',')
    print(f"Extracted channel IDs (len={len(channel_ids_list)}): {channel_ids_list}")
    chunk_size = math.ceil(len(channel_ids_list) / N_CHUNKS) if len(channel_ids_list) >= N_CHUNKS else 1
    channel_chunks = [channel_ids_list[i:i + chunk_size] for i in range(0, len(channel_ids_list), chunk_size)]
    print(f"Channel chunks (len={len(channel_chunks)} chunk_len={len(channel_chunks[0])}): {channel_chunks}")
    return channel_chunks

@dag(
    dag_id='gen_channel_ranking_v3',
    default_args=default_args,
    description='This runs the channel ranking pipeline',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='0 */6 * * *',
    catchup=False  # To avoid backfilling if not required
)
def create_dag():

    fetch_data_task = BashOperator(
        task_id='fetch_channel_data',
        bash_command=f'cd /pipeline && {SHELL_SCRIPT} -w {PIPELINE_DIR} -v {VENV_DIR} -t fetch -c {CSV_PATH}',
        do_xcom_push=True
    )

    @task(max_active_tis_per_dagrun=12)
    def process_channel_chunk(chunk: list):
        chunk_str = ','.join(chunk)
        bash_command = (
            f'cd /pipeline && {SHELL_SCRIPT} -w {PIPELINE_DIR} -v {VENV_DIR} -t process -c {CSV_PATH} '
            f'"{chunk_str}"'
        )
        process_task = BashOperator(
            task_id=f'process_channels_chunk_{hash(chunk_str)}',
            bash_command=bash_command,
            env={'PYTHONUNBUFFERED': '1'}  # Ensures real-time logging
        )
        process_task.execute({})

    extract_ids_task = extract_channel_ids(fetch_data_task.output)

    # Create dynamic tasks
    process_tasks = process_channel_chunk.expand(chunk=extract_ids_task)

    cleanup_db_task = BashOperator(
        task_id='cleanup_db',
        bash_command=f'cd /pipeline && {SHELL_SCRIPT} -w {PIPELINE_DIR} -v {VENV_DIR} -t cleanup -c {CSV_PATH}',
        trigger_rule=TriggerRule.ALL_SUCCESS
    )

    push_to_dune_task = BashOperator(
        task_id='insert_channel_rank_to_dune_v3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh insert_channel_rank_to_dune_v3"
    )

    push_to_s3_task = BashOperator(
        task_id='backup_channel_rank_s3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh channel_rank"
    )

    fetch_data_task >> extract_ids_task >> process_tasks >> cleanup_db_task >> push_to_dune_task >> push_to_s3_task

dag = create_dag()

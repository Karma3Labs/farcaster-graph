from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task, dag
from airflow.utils.trigger_rule import TriggerRule

import math
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

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
    start_date=datetime(2024, 10, 1),
    # schedule_interval='0 */6 * * *',
    schedule_interval=None, # triggered by external trigger
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False  # To avoid backfilling if not required
)
def create_dag():

    fetch_data_task = BashOperator(
        task_id='fetch_channel_data',
        bash_command="cd /pipeline && ./run_channel_scraper_v3.sh -w . -v .venv -t fetch -c channels/Top_Channels.csv",
        do_xcom_push=True
    )

    @task(max_active_tis_per_dagrun=8)
    def process_channel_chunk(chunk: list, interval: int):
        chunk_str = ','.join(chunk)
        bash_command = (
            f'cd /pipeline && ./run_channel_scraper_v3.sh -w . -v .venv -t process -c channels/Top_Channels.csv'
            f' -n {interval}'
            f' "{chunk_str}"'
        )
        process_task = BashOperator(
            task_id=f'process_channels_chunk_{hash(chunk_str)}',
            bash_command=bash_command,
            env={'PYTHONUNBUFFERED': '1'}  # Ensures real-time logging
        )
        process_task.execute({})

    extract_ids_task = extract_channel_ids(fetch_data_task.output)

    # Create dynamic tasks
    process_lifetime_tasks = process_channel_chunk.expand(chunk=extract_ids_task, interval=0)

    process_60d_tasks = process_channel_chunk.expand(chunk=extract_ids_task, interval=60)

    process_7d_tasks = process_channel_chunk.expand(chunk=extract_ids_task, interval=7)

    cleanup_db_task = BashOperator(
        task_id='cleanup_db',
        bash_command="cd /pipeline && ./run_channel_scraper_v3.sh -w . -v .venv -t cleanup -c channels/Top_Channels.csv",
        trigger_rule=TriggerRule.ALL_SUCCESS
    )

    push_to_dune_task = BashOperator(
        task_id='overwrite_channel_rank_in_dune_v3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh overwrite_channel_rank_in_dune_v3"
    )

    push_to_s3_task = BashOperator(
        task_id='backup_channel_rank_s3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh upload_channel_rank_to_s3"
    )

    fetch_data_task >> extract_ids_task >> process_lifetime_tasks >> process_60d_tasks >> process_7d_tasks >> cleanup_db_task >> push_to_dune_task >> push_to_s3_task


dag = create_dag()

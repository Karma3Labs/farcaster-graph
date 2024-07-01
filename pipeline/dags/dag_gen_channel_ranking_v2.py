from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import math

default_args = {
    'owner': 'coder2j',
    'retries': 3,
    'retry_delay': timedelta(minutes=2)
}

PIPELINE_DIR = './'
VENV_DIR = './.venv'
SHELL_SCRIPT = f'{PIPELINE_DIR}/run_channel_scraper_v2.sh'
CSV_PATH = f'{PIPELINE_DIR}/channels/Top_Channels.csv'
N_CHUNKS = 500  # Define the number of chunks

def extract_channel_ids(**kwargs):
    ti = kwargs['ti']
    channel_ids = ti.xcom_pull(task_ids='fetch_channel_data')
    channel_ids_list = channel_ids.split(',')
    print(f"Extracted channel IDs: {channel_ids_list}")
    print(f"number of channels to process: {len(channel_ids_list)}")
    chunk_size = math.ceil(len(channel_ids_list) / N_CHUNKS)
    channel_chunks = [channel_ids_list[i:i + chunk_size] for i in range(0, len(channel_ids_list), chunk_size)]
    print(f"Channel chunks: {channel_chunks}")
    for idx, chunk in enumerate(channel_chunks):
        chunk_str = ','.join(chunk)
        ti.xcom_push(key=f'channel_chunk_{idx}', value=chunk_str)

with DAG(
    dag_id='gen_channel_ranking_v2',
    default_args=default_args,
    description='This runs the channel ranking pipeline',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='0 0 * * *'
) as dag:

    fetch_data_task = BashOperator(
        task_id='fetch_channel_data',
        bash_command=f'cd /pipeline && {SHELL_SCRIPT} -w {PIPELINE_DIR} -v {VENV_DIR} -t fetch -c {CSV_PATH}',
        do_xcom_push=True
    )

    extract_ids_task = PythonOperator(
        task_id='extract_channel_ids',
        python_callable=extract_channel_ids,
        provide_context=True
    )

    fetch_data_task >> extract_ids_task

    for i in range(N_CHUNKS):
        process_channels_task = BashOperator(
            task_id=f'process_channels_chunk_{i}',
            bash_command=(
                f'cd /pipeline && {SHELL_SCRIPT} -w {PIPELINE_DIR} -v {VENV_DIR} -t process -c {CSV_PATH} '
                f'"{{{{ ti.xcom_pull(task_ids="extract_channel_ids", key="channel_chunk_{i}") }}}}"'
            ),
            env={'PYTHONUNBUFFERED': '1'}  # Ensures real-time logging
        )
        extract_ids_task >> process_channels_task
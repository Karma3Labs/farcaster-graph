from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    'owner': 'coder2j',
    'retries': 3,
    'retry_delay': timedelta(minutes=2)
}


with DAG(
    dag_id='gen_channel_ranking',
    default_args=default_args,
    description='This runs run_globaltrust_pipeline.sh without any optimization',
    start_date=datetime(2024, 6, 21, 2),
    schedule_interval='0 */6 * * *'
) as dag:
    task1 = BashOperator(
        task_id='run_channel_scraper.sh',
        bash_command="cd /pipeline && ./run_channel_scraper.sh -w . -v ./.venv"
    )

    task1
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from datetime import datetime, timedelta

db_endpoint = Variable.get('DB_ENDPOINT', default_var="test")
db_user = Variable.get('DB_USER', default_var="test")
db_password = Variable.get('DB_PASSWORD', default_var="test")


default_args = {
    'owner': 'coder2j',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
        'extract_warpcast_channels',
        default_args=default_args,
        description='Fetch channels metadata from WARPCAST API and load into DB daily',
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 8, 19),
        is_paused_upon_creation=True,
        max_active_runs=1,
        catchup=False,
) as dag:
    fetch_data_from_warpcast = BashOperator(
        task_id='fetch_warpcast_data_from_api',
        bash_command="cd /pipeline; extractors/extract_channel_data.sh" 
                        " -w . -v .venv ",
        dag=dag
    )

    fetch_data_from_warpcast

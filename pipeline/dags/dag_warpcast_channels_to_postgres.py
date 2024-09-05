from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from datetime import datetime, timedelta
import subprocess


def fetch_warpcast_data():
    # Fetching variables from Airflow
    db_endpoint = Variable.get('DB_ENDPOINT', default_var="test")
    db_user = Variable.get('DB_USER', default_var="test")
    db_password = Variable.get('DB_PASSWORD', default_var="test")

    # Running the Python script with the parameters
    subprocess.run(["python3", "pipeline/extractors/warpcast_extractor.py", db_endpoint, db_user, db_password],
                   check=True)


default_args = {
    'owner': 'coder2j',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
        'warpcast_api_to_db',
        default_args=default_args,
        description='Fetch data from WARPCAST API and load into DB daily',
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 8, 19),
        is_paused_upon_creation=True,
        max_active_runs=1,
        catchup=False,
) as dag:
    fetch_data_from_warpcast = PythonOperator(
        task_id='fetch_warpcast_data_from_api',
        python_callable=fetch_warpcast_data,
    )

    fetch_data_from_warpcast

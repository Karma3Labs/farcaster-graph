from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from datetime import datetime, timedelta
import subprocess


def fetch_automod_data():
    # Fetching variables from Airflow
    api_key = Variable.get("API_KEY", default_var="api_key")
    db_endpoint = Variable.get('DB_ENDPOINT', default_var="test")
    db_user = Variable.get('DB_USER', default_var="test")
    db_password = Variable.get('DB_PASSWORD', default_var="test")

    # Running the Python script with the parameters
    subprocess.run(["python3", "pipeline/extractors/automod_extractor.py", api_key, db_endpoint, db_user, db_password],
                   check=True)


default_args = {
    'owner': 'coder2j',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
        'automod_api_to_db',
        default_args=default_args,
        description='Fetch data from AUTOMOD API and load into DB daily',
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 9, 4),
        is_paused_upon_creation=True,
        max_active_runs=1,
        catchup=False,
) as dag:
    fetch_data_from_automod = PythonOperator(
        task_id='fetch_data_from_api',
        python_callable=fetch_automod_data,
    )

    fetch_data_from_automod

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from datetime import datetime, timedelta


api_key = Variable.get("API_KEY", default_var="api_key")
db_endpoint = Variable.get('DB_ENDPOINT', default_var="test")
db_user = Variable.get('DB_USER', default_var="test")
db_password = Variable.get('DB_PASSWORD', default_var="test")


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
    fetch_data_from_automod = BashOperator(
        task_id='fetch_automod_data_from_api',
        bash_command=f"cd /pipeline/extractors ; python3 automod_extractor.py {{api_key}} {{ db_user }} {{ db_password }} {{ db_endpoint }}"
    )

    fetch_data_from_automod

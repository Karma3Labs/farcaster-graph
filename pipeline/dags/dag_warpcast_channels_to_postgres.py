from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty
from datetime import datetime, timedelta
import requests
import os
import io
from sqlalchemy import create_engine
from datetime import date
import pandas as pd

# Environment variables
API_KEY = Variable.get('API_KEY')
DB_ENDPOINT = Variable.get('DB_ENDPOINT')
DB_USER = Variable.get('DB_USER')
DB_PASSWORD = Variable.get('DB_PASSWORD')

default_args = {
    'owner': 'coder2j',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}


def fetch_data_from_api():
    initial_url = f"""https://api.warpcast.com/v2/all-channels"""
    response = requests.get(initial_url)

    df_warpcast_channels = pd.DataFrame(response.json()["result"]["channels"])
    df_warpcast_channels.columns = df_warpcast_channels.columns.str.lower()
    df_warpcast_channels['createdat'] = pd.to_datetime(df_warpcast_channels['createdat'], unit='ms')
    df_warpcast_channels["dateiso"] = date.today()

    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (DB_USER, DB_PASSWORD, DB_ENDPOINT, 9541, 'farcaster')

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    with postgres_engine.connect() as connection:
        connection.execute("TRUNCATE TABLE warpcast_channels_data")
        df_warpcast_channels.to_sql('warpcast_channels_data', con=connection, if_exists='append', index=False)

    return None

with DAG(
        'warpcast_api_to_db_dag',
        default_args=default_args,
        description='Fetch data from WARPCAST API and load into DB daily',
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 8, 19),
        catchup=False,
) as dag:
    fetch_data_from_api_task = PythonOperator(
        task_id='fetch_warpcast_data_from_api',
        python_callable=fetch_data_from_api,
    )

    fetch_data_from_api_task

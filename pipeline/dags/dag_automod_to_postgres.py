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
    params = {'start': '2024-01-01', 'end': '2024-12-31'}
    headers = {'api-key': f"""{API_KEY}"""}
    df_automod = pd.DataFrame()
    for channel in ["degen", "dev", "memes"]:
        initial_url = f"""https://automod.sh/api/partners/channels/{channel}/activity/export?"""
        response = requests.get(initial_url, params=params, headers=headers)
        print(response.url)
        if response.status_code == 200:
            # Read the response content into a pandas DataFrame
            data = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            data["channel_id"] = channel
            print(len(data))
            df_automod = pd.concat([df_automod, data], axis=0)
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")

    rename_dict = {
        'createdAt': 'created_at',
        'affectedUsername': 'affected_username',
        'affectedUserFid': 'affected_userid',
        'castHash': 'cast_hash',
        'castText': 'cast_text'
    }

    df_automod.rename(columns=rename_dict, inplace=True)
    df_automod = df_automod[
        ["created_at", "action", "actor", "affected_username", "affected_userid", "cast_hash", "channel_id"]]
    df_automod['created_at'] = pd.to_datetime(df_automod['created_at'], unit='ms')
    df_automod["date_iso"] = date.today()

    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (DB_USER, DB_PASSWORD, DB_ENDPOINT, 9541, 'farcaster')

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    with postgres_engine.connect() as connection:
        df_automod.to_sql('automod_data', con=connection, if_exists='append', index=False)

    return None

with DAG(
        'automod_api_to_db_dag',
        default_args=default_args,
        description='Fetch data from AUTOMOD API and load into DB daily',
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 8, 1),
        catchup=False,
) as dag:
    fetch_data_from_api_task = PythonOperator(
        task_id='fetch_data_from_api',
        python_callable=fetch_data_from_api,
    )

    fetch_data_from_api_task

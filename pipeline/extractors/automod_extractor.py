import pandas as pd
from datetime import date
import requests
from sqlalchemy import create_engine
import io
from loguru import logger


def fetch_data_from_api(api_key, db_user, db_password, db_endpoint):
    params = {'start': '2024-01-01', 'end': '2024-12-31'}
    headers = {'api-key': f"""{api_key}"""}
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

    logger.info(df_automod.head())
    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (db_user, db_password, db_endpoint, 9541, 'farcaster')

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    with postgres_engine.connect() as connection:
        connection.execute("TRUNCATE TABLE automod_data")
        df_automod.to_sql('automod_data', con=connection, if_exists='append', index=False)

    return None


if __name__ == "__main__":
    # Get the parameters from the command line arguments
    fetch_data_from_api('api_key', 'test', 'test', 'test')
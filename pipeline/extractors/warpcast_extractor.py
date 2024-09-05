import requests
import pandas as pd
from datetime import date
from sqlalchemy import create_engine

from loguru import logger


def fetch_data_from_api(db_user, db_password, db_endpoint):
    initial_url = f"""https://api.warpcast.com/v2/all-channels"""
    response = requests.get(initial_url)

    df_warpcast_channels = pd.DataFrame(response.json()["result"]["channels"])
    df_warpcast_channels.columns = df_warpcast_channels.columns.str.lower()
    df_warpcast_channels['createdat'] = pd.to_datetime(df_warpcast_channels['createdat'], unit='ms')
    df_warpcast_channels["dateiso"] = date.today()

    logger.info(df_warpcast_channels.head())

    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (db_user, db_password, db_endpoint, 9541, 'farcaster')

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    with postgres_engine.connect() as connection:
        connection.execute("TRUNCATE TABLE warpcast_channels_data")
        df_warpcast_channels.to_sql('warpcast_channels_data', con=connection, if_exists='append', index=False)

    return None


if __name__ == "__main__":
    # Get the parameters from the command line arguments
    fetch_data_from_api('test', 'test', 'test')

import sys

import requests
import pandas as pd
from datetime import date
from sqlalchemy import create_engine

from loguru import logger


def fetch_data_from_api(db_user, db_password, db_endpoint):
    initial_url = "https://api.warpcast.com/v2/all-channels"
    response = requests.get(initial_url)

    df_warpcast_channels = pd.DataFrame(response.json()["result"]["channels"])
    df_warpcast_channels.columns = df_warpcast_channels.columns.str.lower()
    df_warpcast_channels['createdat'] = pd.to_datetime(df_warpcast_channels['createdat'], unit='ms')
    df_warpcast_channels["dateiso"] = date.today()
    df_warpcast_channels.drop(columns=["moderatorfids"], inplace=True)

    logger.info(df_warpcast_channels.head())
    if len(df_warpcast_channels) == 0:
        raise Exception("Failed to fetch data from warpcast. No data found.")

    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (db_user, db_password, db_endpoint, 9541, 'farcaster')

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    with postgres_engine.connect() as conn:
        with conn.begin():
            conn.execute("TRUNCATE TABLE warpcast_channels_data")
            df_warpcast_channels.to_sql('warpcast_channels_data', con=conn, if_exists='append', index=False)

    return None


if __name__ == "__main__":
    # Get the parameters from the command line arguments
    if len(sys.argv) != 4:
        raise ValueError("Please provide db_user, db_password, and db_endpoint as arguments.")

    db_user = sys.argv[1]
    db_password = sys.argv[2]
    db_endpoint = sys.argv[3]

    fetch_data_from_api(db_user, db_password, db_endpoint)

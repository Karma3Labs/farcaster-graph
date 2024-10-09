from config import settings
import utils

import requests
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
from loguru import logger


def fetch_data_from_api():
    initial_url = "https://api.warpcast.com/v2/all-channels"
    response = requests.get(initial_url)

    df_warpcast_channels = pd.DataFrame(response.json()["result"]["channels"])
    df_warpcast_channels['createdAt'] = pd.to_datetime(df_warpcast_channels['createdAt'], unit='ms')
    df_warpcast_channels.columns = df_warpcast_channels.columns.str.lower()
    db_column_names = [
        "id",
        "url",
        "name",
        "description",
        "imageurl",
        "headerimageurl",
        "leadfid",
        "moderatorfids",
        "createdat",
        "followercount",
        "membercount",
        "pinnedcasthash",
    ]
    df_warpcast_channels = df_warpcast_channels.filter(items=db_column_names, axis=1)
    logger.info(utils.df_info_to_string(df_warpcast_channels, with_sample=True))

    if len(df_warpcast_channels) == 0:
        raise Exception("Failed to fetch data from warpcast. No data found.")

    postgres_engine = create_engine(settings.POSTGRES_URL.get_secret_value(), connect_args={"connect_timeout": 1000})
    try:
        with postgres_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE warpcast_channels_data_v2"))
            df_warpcast_channels.to_sql('warpcast_channels_data_v2', con=conn, if_exists='append', index=False)
    except Exception as e:
        logger.error(f"Failed to insert data into postgres: {e}")
        raise e
    return None


if __name__ == "__main__":
    fetch_data_from_api()

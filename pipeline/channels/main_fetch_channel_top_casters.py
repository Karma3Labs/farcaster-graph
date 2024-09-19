# standard dependencies
import sys
import argparse
from random import sample
import asyncio
from io import StringIO
import json
from datetime import date

# local dependencies
import db_utils
from sqlalchemy import create_engine

from . import channel_utils
from . import channel_db_utils
from config import settings
from timer import Timer

from dotenv import load_dotenv
from loguru import logger
import requests
import pandas as pd

logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)


def fetch_channel_data(csv_path):
    try:
        channel_data = channel_utils.get_seed_fids_from_csv(csv_path)
        channel_ids = channel_data["channel id"].values.tolist()
        channel_ids = [e.lower() for e in channel_ids]
        return channel_ids
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        return []


async def main(csv_path):
    pg_dsn = settings.POSTGRES_ASYNC_URI.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    # get channels
    channel_ids = fetch_channel_data(csv_path)
    all_channels = db_utils.fetch_all_channel_details(pg_url)
    top_channels = all_channels[all_channels.name.isin(channel_ids)]

    # get top casters
    all_casters = []
    for channel in top_channels.iterrows():
        logger.info(channel[1]['id'], channel[1]['url'])
        casters = await channel_db_utils.fetch_top_casters(logger, pg_dsn, channel[1]['id'], channel[1]['url'])
        if len(casters) > 0:
            df = pd.DataFrame(casters)
            df.columns = ['cast_hash', 'fid',
                          'cast_score', 'reaction_count',
                          'global_rank', 'channel_rank',
                          'cast_hour',
                          'cast_ts',
                          'cast_text']
            df['channel_id'] = channel[1]['id']
            all_casters.append(df)
            break
        else:
            pass

    df_top_casters = pd.concat(all_casters)
    df_top_casters['date_iso'] = date.today()
    logger.info(df_top_casters.head())

    engine_string = settings.POSTGRES_URL.get_secret_value()

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    logger.info(postgres_engine)
    with postgres_engine.connect() as connection:
        df_top_casters.to_sql('top_channel_casters', con=connection, if_exists='append', index=False)

    logger.info('top channel casters data updated to DB')

if __name__ == "__main__":
    load_dotenv()
    print(settings)
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", type=str, help="path to the CSV file. For example, -c /path/to/file.csv",
                        required=True)

    args = parser.parse_args()
    print(args)

    logger.debug('hello main')

    asyncio.run(main(args.csv))

# standard dependencies
import sys
import argparse
from pathlib import Path
import random
import urllib.parse

# local dependencies
from config import settings
from channels import channel_utils
import utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
from urllib3.util import Retry
import niquests
from sqlalchemy import create_engine
from sqlalchemy import text

# Configure logger
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

load_dotenv()

def fetch_cura_hide_list() -> pd.DataFrame:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    df = pd.DataFrame()
    with niquests.Session(retries=retries) as session:
        # reuse TCP connection for multiple scm requests
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts=(connect_timeout_s, read_timeout_s)
        url = urllib.parse.urljoin(settings.CURA_FE_API_URL,"/api/channel-hide-list")
        logger.info(f"url: {url}")   
        # TODO parallelize this
        response = session.post(url, json={}, timeout=timeouts)
        res_json = response.json()
        if response.status_code != 200:
            logger.error(f"Failed to fetch channel-hide-list: {res_json}")
            raise Exception(f"Failed to fetch channel-hide-list: {res_json}")
        else:
            logger.trace(f"channel-hide-list: {res_json}")
            # Read the response content into a pandas DataFrame
            data = pd.DataFrame.from_records(res_json.get('data'))
            print(len(data))
            df = pd.concat([df, data], axis=0)
    return df

def main() -> pd.DataFrame:
    df = fetch_cura_hide_list()
    rename_cols = {
        'channelId': 'channel_id',
        'hiddenFid': 'hidden_fid',
        'hiderFid': 'hider_fid',
        'isActive': 'is_active',
        'created_at': 'created_at',
        'updatedAt': 'updated_at',
    }
    df.rename(columns=rename_cols, inplace=True)
    logger.info(utils.df_info_to_string(df, with_sample=True, head=True))
    table_name = 'cura_hidden_fids'
    if settings.IS_TEST:
        logger.info(f"Skipping replace data in the database: {table_name}")
        return
    logger.info(f"Replacing data in the database: {table_name}")
    if settings.IS_TEST:
        logger.warning(f"Skipping replace data in the database: {table_name}")
        return
    try:
        postgres_engine = create_engine(
            settings.POSTGRES_URL.get_secret_value(),
            connect_args={"connect_timeout": 1000},
        )
        with postgres_engine.begin() as conn:
            # within transaction boundary
            conn.execute(text(f"TRUNCATE TABLE {table_name};"))
            df.to_sql(table_name, con=conn, if_exists='append', index=False)
    except Exception as e:
        logger.error(f"Failed to replace data in the database: {e}")
        raise e
    try:
        alt_postgres_engine = create_engine(
            settings.ALT_POSTGRES_URL.get_secret_value(),
            connect_args={"connect_timeout": 1000},
        )
        with alt_postgres_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name};"))
            df.to_sql(table_name, con=conn, if_exists='append', index=False)
    except Exception as e:
        logger.error(f"Failed to replace data in the database: {e}")
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-r",
        "--run",
        action="store_true",
        help="dummy arg to prevent accidental execution",
        required=True
    )
    parser.add_argument(
        "--dry-run",
        help="indicate dry-run mode",
        action="store_true"
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.dry_run:
        settings.IS_TEST = True
    main()
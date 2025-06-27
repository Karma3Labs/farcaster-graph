# standard dependencies
import argparse
import sys

import pandas as pd

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

import cura_utils
import utils

# local dependencies
from config import settings

# Configure logger
logger.remove()
level_per_module = {"": settings.LOG_LEVEL, "silentlib": False}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)

load_dotenv()


def main() -> pd.DataFrame:
    df = cura_utils.fetch_channel_hide_list()
    rename_cols = {
        "channelId": "channel_id",
        "hiddenFid": "hidden_fid",
        "hiderFid": "hider_fid",
        "isActive": "is_active",
        "created_at": "created_at",
        "updatedAt": "updated_at",
    }
    df.rename(columns=rename_cols, inplace=True)
    logger.info(utils.df_info_to_string(df, with_sample=True, head=True))
    table_name = "cura_hidden_fids"
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
            df.to_sql(table_name, con=conn, if_exists="append", index=False)
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
            df.to_sql(table_name, con=conn, if_exists="append", index=False)
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
        required=True,
    )
    parser.add_argument("--dry-run", help="indicate dry-run mode", action="store_true")
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.dry_run:
        settings.IS_TEST = True
    main()

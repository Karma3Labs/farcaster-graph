# standard dependencies
import argparse
import random
import sys
from enum import Enum
from pathlib import Path

import pandas as pd

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

# local dependencies
from config import settings

from . import channel_db_utils, channel_utils

# Performance optimization to avoid copies unless there is a write on shared data
pd.set_option("mode.copy_on_write", True)

# Configure logger
logger.remove()
level_per_module = {"": settings.LOG_LEVEL, "db_utils": "DEBUG", "silentlib": False}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)

load_dotenv()


def process_channels(
    channel_seeds_csv: Path,
    channel_bots_csv: Path,
    channel_ids_str: str,
    interval: int = 0,
):
    # Setup connection pool for querying Warpcast API

    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_bots_df = channel_utils.read_channel_bot_fids_csv(channel_bots_csv)
    channel_ids = channel_ids_str.split(",")
    missing_seed_fids = []

    for cid in channel_ids:
        try:
            channel_lt_df, pretrust_fids, absent_fids = channel_utils.prep_trust_data(
                cid, channel_seeds_df, channel_bots_df, pg_dsn, pg_url, interval
            )

            if len(channel_lt_df) == 0:
                if interval > 0:
                    logger.info(
                        f"No local trust for channel {cid} for interval {interval}"
                    )
                    continue
                else:
                    logger.error(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )
                    # this is unexpected because if a channel exists there must exist at least one ijv
                    raise Exception(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )
            # Future Feature: keep track and clean up seed fids that have had no engagement in channel
            missing_seed_fids.append({cid: absent_fids})

            df = channel_utils.compute_goeigentrust(
                cid=cid,
                channel_lt_df=channel_lt_df,
                pretrust_fids=pretrust_fids,
                interval=interval,
            )
            if df is not None:
                channel_db_utils.insert_channel_scores_df(
                    logger=logger, cid=cid, scores_df=df, pg_url=pg_url
                )

        except Exception as e:
            logger.error(f"failed to process a channel: {cid}: {e}")
            raise e

    logger.info(missing_seed_fids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--csv",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=True,
    )
    parser.add_argument(
        "-b",
        "--bots",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=False,
    )
    parser.add_argument(
        "-t",
        "--task",
        type=str,
        help="task to perform: fetch or process",
        required=True,
    )
    parser.add_argument(
        "-ids",
        "--channel_ids",
        type=str,
        help="channel IDs for processing, only used for process task",
        required=False,
    )
    parser.add_argument(
        "-int",
        "--interval",
        type=int,
        help="number of days to consider for processing, 0 means lifetime",
        required=False,
    )

    args = parser.parse_args()
    print(args)
    logger.info(settings)

    logger.debug("hello main")

    if args.task == "fetch":
        channel_ids = channel_utils.read_channel_ids_csv(args.csv)
        random.shuffle(channel_ids)  # in-place shuffle
        print(
            ",".join(channel_ids)
        )  # Print channel_ids as comma-separated for Airflow XCom
    elif args.task == "process":
        if (
            not hasattr(args, "channel_ids")
            or not hasattr(args, "interval")
            or not hasattr(args, "bots")
        ):
            logger.error(
                "Channel IDs, Bot FIDs and Interval are required for processing."
            )
            sys.exit(1)
        process_channels(
            channel_seeds_csv=args.csv,
            channel_bots_csv=args.bots,
            channel_ids_str=args.channel_ids,
            interval=args.interval,
        )
    else:
        logger.error("Invalid task specified. Use 'fetch' or 'process'.")
        sys.exit(1)

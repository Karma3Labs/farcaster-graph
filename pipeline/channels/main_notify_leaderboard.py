# standard dependencies
import argparse
import sys

import niquests
import numpy as np
import pandas as pd

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from urllib3.util import Retry

import cura_utils
import utils

# local dependencies
from config import settings

from . import channel_db_utils

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


def group_and_chunk_df(
    df: pd.DataFrame, group_by_columns: list[str], collect_column: str, chunk_size: int
) -> pd.DataFrame:
    def chunk_list(x):
        return [chunk for chunk in np.array_split(x, np.ceil(len(x) / chunk_size))]

    return df.groupby(group_by_columns)[collect_column].agg(list).apply(chunk_list)


def notify():
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    (cutoff_time, entries_df) = channel_db_utils.fetch_notify_entries(
        logger,
        pg_dsn,
        settings.POSTGRES_TIMEOUT_MS,
    )
    logger.info(
        f"Channel fids to be notified: {utils.df_info_to_string(entries_df, with_sample=True)}"
    )

    # Get top 50 earners per channel
    top_50_per_channel = (
        entries_df.sort_values(["channel_id", "earnings"], ascending=[True, False])
        .groupby("channel_id")
        .head(50)
    )

    logger.info(
        f"Top 50 earners per channel: {utils.df_info_to_string(top_50_per_channel, with_sample=True)}"
    )

    if settings.IS_TEST:
        chunk_size = 2
    else:
        chunk_size = settings.CURA_NOTIFY_CHUNK_SIZE

    chunked_df = group_and_chunk_df(
        top_50_per_channel, ["channel_id", "is_token"], "fid", chunk_size
    )
    logger.info(
        f"Channel fids to be notified: {utils.df_info_to_string(chunked_df, with_sample=True, head=True)}"
    )

    chunked_df = chunked_df.sort_index(level="is_token", ascending=False)
    logger.info(
        f"Sorted and chunked fids: {utils.df_info_to_string(chunked_df, with_sample=True, head=True)}"
    )

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET", "POST"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    with niquests.Session(retries=retries) as session:
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)
        for (channel_id, is_token), fids in chunked_df.items():
            for fids_chunk in fids:
                fids_chunk = fids_chunk.tolist()

                logger.info(
                    f"Sending notification for channel={channel_id} :is_token={is_token} :fids={fids_chunk}"
                )
                cura_utils.leaderboard_notify(
                    session, timeouts, channel_id, is_token, fids_chunk, cutoff_time
                )

            logger.info(f"Notifications sent for channel '{channel_id}'")
        logger.info("Notifications sent for all channels")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
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

    notify()

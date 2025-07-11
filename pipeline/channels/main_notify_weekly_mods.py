# standard dependencies
import argparse
import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path

import niquests

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from urllib3.util import Retry

import cura_utils
import utils

# local dependencies
from config import settings

from . import channel_db_utils, channel_utils

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


async def notify(channel_bots_csv: str, since: datetime):
    pg_url = settings.ALT_POSTGRES_URL.get_secret_value()

    fids = cura_utils.fetch_frame_users()
    fid_set = set(fids)
    logger.info(f"Found {len(fid_set)} frame users")
    logger.info(
        f"Sample of frame users: {random.sample(list(fid_set), min(10, len(fid_set)))}"
    )
    logger.trace(f"Frame users: {fid_set}")

    channel_bots_df = channel_utils.read_channel_bot_fids_csv(channel_bots_csv)
    bot_fids = channel_bots_df["FID"].values.tolist()
    logger.info(
        f"Frame users that are bots: {set.intersection(fid_set, set(bot_fids))}"
    )
    fid_set = fid_set - set(bot_fids)

    channels_df = channel_db_utils.fetch_channel_mods_with_metrics(
        logger, pg_url, since.isoformat(), notification_threshold=10
    )
    logger.info(f"Total number of channels: {len(channels_df)}")
    logger.info(utils.df_info_to_string(channels_df, with_sample=True))

    if settings.IS_TEST:
        fid_set = {725, 2025, 2075, 516917, 563958, 17866}

    def filter_mods(arr):
        return [x for x in arr if x in fid_set]

    channels_df["notify_mods"] = channels_df["mods"].apply(filter_mods)
    channels_df = channels_df[channels_df["notify_mods"].apply(len) > 0]
    logger.info(f"Number of channels with mods to notify: {len(channels_df)}")
    logger.info(utils.df_info_to_string(channels_df, with_sample=True))

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    with niquests.Session(retries=retries) as session:
        # reuse TCP connection for multiple scm requests
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)

        for row in channels_df.itertuples():
            logger.debug(f"Processing channel {row.channel_id}")
            logger.debug(f"Channel mods before filter: {row.notify_mods}")
            notify_mods = set(row.notify_mods) & fid_set
            logger.debug(f"Channel mods after filter: {notify_mods}")
            if len(notify_mods) == 0:
                logger.info(f"No mods to notify for channel {row.channel_id}")
                continue
            cura_utils.weekly_mods_notify(
                session=session,
                timeouts=timeouts,
                channel_id=row.channel_id,
                fids=list(notify_mods),
            )
            logger.info(
                f"Sent notifications for channel {row.channel_id} to {len(notify_mods)} fids"
            )
            # shrink filter so we can avoid notifying mods again
            fid_set = fid_set - set(notify_mods)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        "--bots-csv",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=True,
    )
    parser.add_argument("--dry-run", help="indicate dry-run mode", action="store_true")
    parser.add_argument(
        "-s",
        "--since",
        type=lambda dtstr: datetime.fromisoformat(dtstr),
        help="datetime in ISO 8601 format since which to fetch notifications",
        required=True,
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.dry_run:
        settings.IS_TEST = True

    asyncio.run(notify(args.bots_csv, args.since))

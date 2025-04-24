# standard dependencies
import sys
import argparse
from pathlib import Path
from itertools import batched
import random
import asyncio

# local dependencies
from config import settings
from . import channel_db_utils
import cura_utils
from . import channel_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import niquests
from urllib3.util import Retry

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

async def notify(channels_csv: str):
    pg_dsn = settings.ALT_POSTGRES_ASYNC_URI.get_secret_value()

    fids = cura_utils.fetch_frame_users()
    fid_set = set(fids)
    logger.info(f"Found {len(fid_set)} frame users")
    logger.info(f"Sample of frame users: {random.sample(list(fid_set), min(10, len(fid_set)))}")
    logger.trace(f"Frame users: {fid_set}")

    cids_df = channel_utils.read_trending_channel_ids_csv(channels_csv)
    cids = cids_df['ChannelID'].values.tolist()
    logger.info(f"Listed channels: {cids}")

    sorted_channel_scores = await channel_db_utils.fetch_channels_trend_score (
        logger=logger, pg_dsn=pg_dsn, channel_ids=cids
    )
    sorted_cids = [channel_sore['id'] for channel_sore in sorted_channel_scores]

    logger.info(f"Sorted channels: {sorted_cids}")

    if settings.IS_TEST:
        fid_set = {725, 2025, 2075, 516917, 563958, 17866}
        sorted_cids = ['spih', 'openrank', 'curaverse']

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
        timeouts=(connect_timeout_s, read_timeout_s)

        for cid in sorted_cids:
            logger.info(f"Processing channel {cid} for {len(fid_set)} fids")
            notified_fids = []
            for batch_set in batched(fid_set, settings.FID_BATCH_SIZE):
                filtered_fids = await channel_db_utils.filter_channel_followers(
                    logger=logger, pg_dsn=pg_dsn, channel_id=cid, fids=batch_set,
                )
                filtered_fids = [fid['fid'] for fid in filtered_fids]
                logger.debug(f"Filtered fids: {filtered_fids}")

                cura_utils.daily_cast_notify(
                    session=session,
                    timeouts=timeouts,
                    channel_id=cid,
                    fids=filtered_fids
                )
                notified_fids.extend(filtered_fids)
            logger.info(f"Sent notifications for channel {cid} to {len(notified_fids)} fids")        
            fid_set = fid_set - set(notified_fids)
    return

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
        "--dry-run",
        help="indicate dry-run mode",
        action="store_true"
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.dry_run:
        settings.IS_TEST = True

    asyncio.run(notify(args.csv))
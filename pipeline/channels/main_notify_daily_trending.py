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
    fids = set(fids)
    logger.info(f"Found {len(fids)} frame users")
    logger.info(f"Sample of frame users: {random.sample(fids, min(10, len(fids)))}")
    logger.trace(f"Frame users: {fids}")

    cids_df = channel_utils.read_trending_channel_ids_csv(channels_csv)
    cids = cids_df['ChannelID'].values.tolist()

    # TODO sort channels by trending score > 0
    logger.info(f"Trending channels: {cids}")

    if settings.IS_TEST:
        fids = fids[:5]
        cids = cids[:5]

    for cid in cids:
        logger.info(f"Processing channel {cid}")
        for batch in batched(fids, settings.FID_BATCH_SIZE):
            filtered_fids = await channel_db_utils.filter_channel_followers(
                logger=logger, pg_dsn=pg_dsn, channel_id=cid, fids=batch,
            )
            logger.debug(f"Filtered fids: {filtered_fids}")
            # TODO send notification
            # TODO remove filtered fids from set
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
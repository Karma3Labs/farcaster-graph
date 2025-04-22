# standard dependencies
import sys
import argparse
from pathlib import Path

# local dependencies
from config import settings
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

def notify(channels_csv: str):
    fids = cura_utils.fetch_frame_users()
    logger.debug(f"Frame users: {fids}")

    cids = channel_utils.read_trending_channel_ids_csv(channels_csv)
    logger.debug(f"Trending channels: {cids}")
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

    notify(args.csv)
# standard dependencies
import sys
import argparse

# local dependencies
from config import settings
import cura_utils

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

def notify():
    fids = cura_utils.fetch_frame_users()
    logger.debug(f"Frame users: {fids}")
    return

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
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

    notify()
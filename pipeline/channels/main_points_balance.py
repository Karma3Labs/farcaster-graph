# standard dependencies
import sys
import argparse


# local dependencies
from config import settings
from . import channel_db_utils

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

def main():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_secs = 120_000
    channel_db_utils.update_points_balance_v2(logger, pg_dsn, sql_timeout_secs)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="store_true",
        help="dummy arg to prevent accidental execution"
    )

    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.run:
        logger.info('hello main')
        main()
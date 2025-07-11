# standard dependencies
import argparse
import datetime
import sys

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

# local dependencies
from config import settings

from . import channel_db_utils
from .channel_db_utils import Metric

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


def main():
    # Metrics only available in Eigen 8
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = 120_000
    channel_db_utils.upsert_weekly_metrics(
        logger, pg_dsn, sql_timeout_ms, Metric.WEEKLY_NUM_CASTS
    )
    channel_db_utils.upsert_weekly_metrics(
        logger, pg_dsn, sql_timeout_ms, Metric.WEEKLY_UNIQUE_CASTERS
    )


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

    main()

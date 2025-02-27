# standard dependencies
import sys
import argparse
from datetime import datetime
import asyncio
from enum import Enum

# local dependencies
from config import settings, Database
from . import cast_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

class FillType(str, Enum):
    default = "default"
    backfill = "backfill"
    gapfill = "gapfill"


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

async def main(
    database: Database,
    daemon: bool,
    fill_type: FillType,
    target_date: datetime,
    target_month: datetime,
):
    while True:
        match database:
            case Database.EIGEN2:
                pg_dsn = settings.POSTGRES_DSN.get_secret_value()
                pg_host = settings.DB_HOST
            case Database.EIGEN8:
                pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
                pg_host = settings.ALT_DB_HOST
            case _:
                raise ValueError(f"Unknown database: {database}")

        match fill_type:
            case FillType.default:
                logger.info(f"inserting k3l_cast_action into {pg_host}")
                cast_db_utils.insert_cast_action(
                    logger, pg_dsn, settings.CASTS_BATCH_LIMIT
                )
            case FillType.backfill:
                logger.info(f"backfilling k3l_cast_action into {pg_host}")
                cast_db_utils.backfill_cast_action(
                    logger, pg_dsn, settings.CASTS_BATCH_LIMIT, target_month
                )

            case FillType.gapfill:
                logger.info(f"gapfilling k3l_cast_action into {pg_host}")
                cast_db_utils.gapfill_cast_action(
                    logger, pg_dsn, settings.CASTS_BATCH_LIMIT, target_date
                )

        sleep_duration = settings.CASTS_SLEEP_SECS
        if daemon:
            logger.info(f"sleeping for {sleep_duration}s")
            await asyncio.sleep(sleep_duration)
            logger.info(f"waking up after {sleep_duration}s sleep")
        else:
            logger.info("bye bye")
            break # don't go into infinite loop
  # end while loop


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "-d", "--daemon",
    help="set or not",
    action="store_true"
  )
  parser.add_argument(
    "-f",
    "--fill-type",
    choices=list(FillType),
    default=FillType.default,
    type=FillType,
    help="fill type",
    required=False,
  )
  parser.add_argument(
    "-p",
    "--postgres",
    choices=list(Database),
    default=Database.EIGEN2,
    type=Database,
    help="eigen2 or eigen8",
    required=False,
  )
  parser.add_argument(
    "-t",
    "--target-date",
    help="Date for gapfill, format: YYYY-MM-DD HH:MM:SS",
    required=False,
    type=lambda d: datetime.strptime(d, "%Y-%m-%d %H:%M:%S"),
  )
  parser.add_argument(
    "-m",
    "--target-month",
    help="Month for backfill, format: YYYY-MM",
    required=False,
    type=lambda d: datetime.strptime(d, "%Y-%m"),
  )

  args = parser.parse_args()
  print(args)

  load_dotenv()
  print(settings)

  if args.fill_type == FillType.gapfill:
    if args.target_date is None:
      raise ValueError("target-date is required for gapfill")
  if args.fill_type == FillType.backfill:
    if args.target_month is None:
      raise ValueError("target-month is required for backfill")

  logger.info('hello hello')
  asyncio.run(main(args.postgres, args.daemon, args.fill_type, args.target_date, args.target_month))
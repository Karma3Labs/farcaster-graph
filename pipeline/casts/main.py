# standard dependencies
import sys
import argparse
from datetime import datetime
import asyncio
from enum import StrEnum

# local dependencies
from config import settings
from . import cast_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

class FillType(StrEnum):
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

async def main(daemon: bool, fill_type: FillType, target_date: str):
  while True:
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    alt_pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()

    match fill_type:
      case FillType.default:
        logger.info(f"inserting k3l_cast_action into {settings.DB_HOST}")
        cast_db_utils.insert_cast_action(logger,
                                              pg_dsn,
                                              settings.CASTS_BATCH_LIMIT)

        logger.info(f"inserting k3l_cast_action into {settings.ALT_REMOTE_DB_HOST}")
        cast_db_utils.insert_cast_action(logger,
                                              alt_pg_dsn,
                                              settings.CASTS_BATCH_LIMIT)

      case FillType.backfill:
        logger.info(f"backfilling k3l_cast_action into {settings.DB_HOST}")
        cast_db_utils.backfill_cast_action(logger,
                                              pg_dsn,
                                              settings.CASTS_BATCH_LIMIT)

        logger.info(f"backfilling k3l_cast_action into {settings.ALT_REMOTE_DB_HOST}")
        cast_db_utils.backfill_cast_action(logger,
                                              alt_pg_dsn,
                                              settings.CASTS_BATCH_LIMIT)
      case FillType.gapfill:
        logger.info(f"gapfilling k3l_cast_action into {settings.DB_HOST}")
        cast_db_utils.gapfill_cast_action(logger,
                                              pg_dsn,
                                              settings.CASTS_BATCH_LIMIT,
                                              target_date)

        logger.info(f"gapfilling k3l_cast_action into {settings.ALT_REMOTE_DB_HOST}")
        cast_db_utils.gapfill_cast_action(logger,
                                              alt_pg_dsn,
                                              settings.CASTS_BATCH_LIMIT,
                                              target_date)

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
  parser.add_argument("-d", "--daemon",
                   help="set or not",
                   action="store_true")
  
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
    "-t",
    "--target-date",
    help="Date condition for the queries, format: YYYY-MM-DD",
    required=False,
    type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
  )

  args = parser.parse_args()
  print(args)

  load_dotenv()
  print(settings)

  target_date:str = None
  if args.fill_type == FillType.gapfill:
    if args.target_date is None:
      raise ValueError("target-date is required for gapfill")
    if args.target_date:
      target_date = args.target_date.strftime("%Y-%m-%d")

  logger.info('hello hello')
  asyncio.run(main(args.daemon, args.fill_type, target_date))
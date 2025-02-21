# standard dependencies
import sys
import argparse
from random import sample
import asyncio

# local dependencies
from config import settings
from timer import Timer
from . import cast_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

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


async def main(daemon: bool):
  while True:
    sleep_duration = settings.CASTS_SLEEP_SECS
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    logger.info(f"inserting k3l_cast_action into {settings.DB_HOST}")
    cast_db_utils.insert_cast_action(logger,
                                          pg_dsn,
                                          settings.CASTS_BATCH_LIMIT)

    pg_dsn_8 = settings.ALT_POSTGRES_DSN.get_secret_value()
    logger.info(f"inserting k3l_cast_action into {settings.ALT_REMOTE_DB_HOST}")
    cast_db_utils.insert_cast_action(logger,
                                          pg_dsn_8,
                                          settings.CASTS_BATCH_LIMIT)

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
                   default=False,
                   type=lambda x: (str(x).lower() == 'true'))
  
  args = parser.parse_args()
  print(args)

  load_dotenv()
  print(settings)

  logger.info('hello hello')
  asyncio.run(main(args.daemon))
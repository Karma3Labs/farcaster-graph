# standard dependencies
import sys
import time
from random import sample
import asyncio

# local dependencies
from config import settings
from . import frames_db_utils
from . import scrape_utils
from timer import Timer

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


async def main():
  logger.debug(f"{settings.FRAMES_TIMER_SECS}s job current time : {time.ctime()}")
  pg_dsn = settings.POSTGRES_DSN.get_secret_value()

  url_records = frames_db_utils.fetch_unprocessed_urls(logger, 
                                                       pg_dsn, 
                                                       settings.FRAMES_SCRAPE_CONCURRENCY)
  logger.info(f"Fetched {len(url_records)} rows from db")
  logger.info(f"Sample rows: {sample(url_records, 5)}")

  tasks = []
  with Timer(name="categorize_url"):
    for record in url_records:
        tasks.append(
          asyncio.create_task(
            scrape_utils.categorize_url(logger=logger,
                                        url_id=record[0],
                                        url=record[1],
                                        timeout=settings.FRAMES_SCRAPE_TIMEOUT_SECS)))
    url_categories = await asyncio.gather(*tasks, return_exceptions=True)
  logger.info(f"Sample rows: {sample(url_categories, 5)}")

  frames_db_utils.update_urls(logger, pg_dsn, url_categories)

if __name__ == "__main__":
  load_dotenv()
  print(settings)

  logger.debug('hello main')
  asyncio.run(main())
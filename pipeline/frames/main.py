# standard dependencies
import sys
import time
from random import sample
import asyncio

import aiohttp

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
  while True:
    sleep_duration = settings.FRAMES_SLEEP_SECS
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()

    url_records = frames_db_utils.fetch_unparsed_urls(logger,
                                                        pg_dsn,
                                                        settings.FRAMES_BATCH_SIZE)
    logger.info(f"Fetched {len(url_records)} unparsed rows from db")
    logger.info(f"Sample rows: {sample(url_records, min(5, len(url_records)))}")

    if len(url_records) > 0:
      url_parts = [scrape_utils.parse_url(logger=logger,
                                          url_id=record[0],
                                          url=record[1]) for record in url_records]

      logger.info(f"Parsed {len(url_parts)} rows")
      logger.info(f"Sample rows: {sample(url_parts, min(5, len(url_parts)))}")

      frames_db_utils.update_url_parts(logger, pg_dsn, url_parts)

      # there may be more rows to process, nap don't sleep
      sleep_duration = settings.FRAMES_NAP_SECS
    # end if len(url_records) > 0

    url_records = frames_db_utils.fetch_unprocessed_urls(logger,
                                                        pg_dsn,
                                                        settings.FRAMES_BATCH_SIZE)
    logger.info(f"Fetched {len(url_records)} unprocessed rows from db")
    logger.info(f"Sample rows: {sample(url_records, min(5, len(url_records)))}")

    if len(url_records) > 0:
      http_timeout = aiohttp.ClientTimeout(total=settings.FRAMES_SCRAPE_TIMEOUT_SECS)
      connector = aiohttp.TCPConnector(ttl_dns_cache=3000, limit=settings.FRAMES_SCRAPE_CONCURRENCY)
      http_conn_pool = aiohttp.ClientSession(connector=connector, timeout=http_timeout)
      tasks = []
      with Timer(name="categorize_url"):
        async with http_conn_pool:
          for record in url_records:
              tasks.append(
                asyncio.create_task(
                  scrape_utils.categorize_url(logger=logger,
                                              url_id=record[0],
                                              url=record[1],
                                              session=http_conn_pool)))
          # end task append loop
          url_categories = await asyncio.gather(*tasks, return_exceptions=True)
        #end http_conn_pool
      # end timer
      logger.info(url_categories)
      frames_db_utils.update_url_categories(logger, pg_dsn, url_categories)
      # there may be more rows to process, nap don't sleep
      sleep_duration = settings.FRAMES_NAP_SECS
    # end if len(url_records) > 0

    logger.info(f"sleeping for {sleep_duration}s")
    await asyncio.sleep(sleep_duration)
    logger.info(f"waking up after {sleep_duration}s sleep")
  # end infinite loop


if __name__ == "__main__":
  # TODO don't depend on current directory to find .env
  load_dotenv()
  print(settings)

  logger.debug('hello main')
  asyncio.run(main())
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
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()

    url_records = frames_db_utils.fetch_unprocessed_urls(logger, 
                                                        pg_dsn, 
                                                        settings.FRAMES_BATCH_SIZE)
    logger.info(f"Fetched {len(url_records)} rows from db")
    logger.info(f"Sample rows: {sample(url_records, 5)}")

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
        url_categories = await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"Sample rows: {sample(url_categories, 5)}")
    logger.info(url_categories)

    frames_db_utils.update_urls(logger, pg_dsn, url_categories)

    logger.info(f"sleeping for {settings.FRAMES_TIMER_SECS}s")
    await asyncio.sleep(settings.FRAMES_TIMER_SECS)
    logger.info(f"waking up after {settings.FRAMES_TIMER_SECS}s sleep")


if __name__ == "__main__":
  load_dotenv()
  print(settings)

  logger.debug('hello main')
  asyncio.run(main())
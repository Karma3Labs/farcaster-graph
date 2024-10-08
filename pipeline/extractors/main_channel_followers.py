import argparse
from datetime import datetime
import sys
import asyncio
from enum import Enum
from pathlib import Path

import asyncpg

from config import settings
from extractors.channel_extractor_utils import (
    fetch_all_channels_warpcast,
    process_channel,
)
from timer import Timer
from channels import channel_utils

import aiohttp
import pandas as pd
from loguru import logger


pd.set_option("mode.copy_on_write", True)

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "db_utils": "DEBUG",
    "silentlib": False
}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module, # type: ignore
    level=0,
) # type: ignore


class Scope(Enum):
  top = 1
  all = 2

  def __str__(self):
    return self.name

  @staticmethod
  def from_string(s):
    try:
        return Scope[s]
    except KeyError:
        raise ValueError()

async def main(daemon: bool, scope: Scope, csv_path: Path):
    while True:
        try:

            logger.info(f"Reading all top channels from CSV:{csv_path}")
            top_channel_ids = channel_utils.read_channel_ids_csv(csv_path)
            logger.info(f"Total number of top channels: {len(top_channel_ids)}")
            logger.info(f"First 10 top channel ids: {top_channel_ids[:10]}")

            if scope == Scope.top:
                channel_ids = top_channel_ids
            elif scope == Scope.all:
                logger.info("Fetching all Warpcast channels:")
                all_channel_ids = await fetch_all_channels_warpcast()
                logger.info(f"Total number of channels: {len(all_channel_ids)}")
                logger.info(f"First 10 channel ids: {all_channel_ids[:10]}")
                channel_ids = list(set(all_channel_ids) - set(top_channel_ids))
            else:
                raise ValueError
            
            if settings.IS_TEST:
                channel_ids = channel_ids[:settings.TEST_CHANNEL_LIMIT]

            logger.info(f"Total number of channels to fetch: {len(channel_ids)}")
            logger.info(f"First 10 channel ids to fetch: {channel_ids[:10]}")

            http_timeout = aiohttp.ClientTimeout(sock_connect=settings.WARPCAST_CHANNELS_TIMEOUT_SECS,
                                                sock_read=settings.WARPCAST_CHANNELS_TIMEOUT_SECS)
            connector = aiohttp.TCPConnector(ttl_dns_cache=3000, limit=settings.WARPCAST_PARALLEL_REQUESTS)

            db_pool = await asyncpg.create_pool(settings.POSTGRES_ASYNC_URI.get_secret_value(),
                                            min_size=1,
                                            max_size=settings.POSTGRES_POOL_SIZE)

            job_time = datetime.now()
            with Timer(name="process_channels"):
                async with aiohttp.ClientSession(connector=connector) as http_conn_pool:
                    for i in range(0, len(channel_ids), settings.WARPCAST_PARALLEL_REQUESTS):
                        tasks = []
                        batch = channel_ids[i:i + settings.WARPCAST_PARALLEL_REQUESTS]
                        logger.info(f"batch[{i},{i + settings.WARPCAST_PARALLEL_REQUESTS}]:{batch} channels to process")
                        for channel_id in batch:
                            tasks.append(
                                asyncio.create_task(
                                    process_channel(
                                        job_time=job_time,
                                        db_pool=db_pool, # type: ignore
                                        http_conn_pool=http_conn_pool,
                                        http_timeout=http_timeout,
                                        channel_id=channel_id,
                                    )
                                )
                            )
                        channel_followers = await asyncio.gather(*tasks, return_exceptions=True)
                        logger.info(f"batch[{i},{i + settings.WARPCAST_PARALLEL_REQUESTS}]:{len(channel_followers)} channels processed")

            if daemon:
                logger.info(f"sleeping for {settings.DAEMON_SLEEP_SECS}s before the next run of this job")
                await asyncio.sleep(settings.DAEMON_SLEEP_SECS)
                logger.info(f"waking up after {settings.DAEMON_SLEEP_SECS}s sleep")
            else:
                logger.info("bye bye")
                break  # don't go into infinite loop
        finally:
            if db_pool:
                await db_pool.close()
    # end while loop


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
        "-s",
        "--scope",
        help="top or all",
        required=True,
        choices=list(Scope),
        type=Scope.from_string,
    )
    parser.add_argument(
        "-d",
        "--daemon",
        help="set or not",
        default=False,
        action="store_true"
    )

    args = parser.parse_args()
    print(args)

    logger.info("hello hello")
    asyncio.run(main(args.daemon, args.scope, args.csv))
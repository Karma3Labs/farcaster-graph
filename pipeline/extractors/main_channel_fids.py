import argparse
from datetime import datetime
import sys
import asyncio
from enum import Enum
from pathlib import Path

import asyncpg

from config import settings
from extractors import channel_extractor_utils
from extractors.channel_extractor_utils import JobType
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
  top = 'top'
  all = 'all'

async def fetch(daemon: bool, scope: Scope, job_type: JobType, csv_path: Path):
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
                all_channel_ids = await channel_extractor_utils.fetch_all_channels_warpcast()
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
                                    channel_extractor_utils.process_channel(
                                        job_type=job_type,
                                        job_time=job_time,
                                        db_pool=db_pool, # type: ignore
                                        http_conn_pool=http_conn_pool,
                                        http_timeout=http_timeout,
                                        channel_id=channel_id,
                                    )
                                )
                            )
                        channel_followers = await asyncio.gather(*tasks, return_exceptions=True)
                        exceptions = [t for t in channel_followers if isinstance(t, Exception)]
                        if len(exceptions) > 0: 
                            logger.error(f"Error processing channels: {exceptions}")
                            if job_type == JobType.members:
                                # warpcast_members table is replaced with every run. 
                                # so, fail the whole job even for 1 channel failure
                                raise Exception("Error processing channels")
                            else:
                                # warpcast_followers table only deletes channels that have had new successful runs
                                # don't fail the whole job
                                pass
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

def replace_old_data(job_type: JobType):
    if job_type == JobType.followers:
        # followers job allows for failures in fetching
        # don't cleanup the whole table
        raise Exception("DANGER: don't use cleanup for followers job")
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_milliseconds = settings.POSTGRES_TIMEOUT_SECS * 1_000
    channel_extractor_utils.replace_db(pg_dsn, sql_timeout_milliseconds, job_type)

def merge_old_data(job_type: JobType):
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_milliseconds = settings.POSTGRES_TIMEOUT_SECS * 1_000
    channel_extractor_utils.merge_db(pg_dsn, sql_timeout_milliseconds, job_type)

def prepare(job_type: JobType):
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_milliseconds = settings.POSTGRES_TIMEOUT_SECS * 1_000
    channel_extractor_utils.prepare_db(pg_dsn, sql_timeout_milliseconds, job_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="subcommand", 
        title="subcommands", 
        help="fetch or cleanup",
        required=True,
    )

    prep_parser = subparsers.add_parser("prep", help="prepare db")
    fetch_parser = subparsers.add_parser("fetch", help="fetch data from warpcast")
    cleanup_parser = subparsers.add_parser("cleanup", help="cleanup old data from db")

    fetch_parser.add_argument(
        "-j",
        "--job_type",
        help="followers or members",
        required=True,
        choices=list(JobType),
        type=JobType.from_string,
    )
    fetch_parser.add_argument(
        "-c",
        "--csv",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=True,
    )
    fetch_parser.add_argument(
        "-s",
        "--scope",
        help="top or all",
        required=True,
        choices=list(Scope),
        type=Scope,
    )
    fetch_parser.add_argument(
        "-d",
        "--daemon",
        help="set or not",
        default=False,
        action="store_true"
    )
    cleanup_parser.add_argument(
        "-j",
        "--job_type",
        help="followers or members",
        required=True,
        choices=list(JobType),
        type=JobType.from_string,
    )
    prep_parser.add_argument(
        "-j",
        "--job_type",
        help="followers or members",
        required=True,
        choices=list(JobType),
        type=JobType.from_string,
    )
    args = parser.parse_args()
    print(args)

    logger.info("hello hello")
    if args.subcommand == "prep":
        prepare(args.job_type)
    elif args.subcommand == "cleanup":
        if args.job_type == JobType.members:
            replace_old_data(args.job_type)
        elif args.job_type == JobType.followers:
            merge_old_data(args.job_type)
    elif args.subcommand == "fetch":
        asyncio.run(fetch(args.daemon, args.scope, args.job_type, args.csv))
    else: 
        parser.print_help()
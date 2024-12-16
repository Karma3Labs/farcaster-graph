from enum import Enum
import random
import time
import asyncio
from typing import Any
import datetime
import psycopg2
import json

from config import settings

from loguru import logger
import aiohttp
from asyncpg.pool import Pool

class JobType(Enum):
    followers = {
        "url": 'https://api.warpcast.com/v1/channel-followers',
        "live_table": 'warpcast_followers',
        "columns": ["fid", "followedat", "insert_ts", "channel_id"]
    }
    members = {
        "url": 'https://api.warpcast.com/fc/channel-members',
        "live_table": 'warpcast_members',
        "columns": ["fid", "memberat", "insert_ts", "channel_id"]
    }

    def __str__(self):
        return self.name

    @staticmethod
    def from_string(s):
        try:
            return JobType[s]
        except KeyError:
            raise ValueError()


async def fetch_all_channels_warpcast():
    url = "https://api.warpcast.com/v2/all-channels"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"Status: {response.status}")
            data = await response.json()

            channels = data.get('result', {}).get('channels', [])
            logger.info(f"Total number of channels: {len(channels)}")

            channel_ids = [channel['id'] for channel in channels]

            return channel_ids


async def fetch_channel_fids(
        job_type: JobType,
        http_conn_pool: aiohttp.ClientSession,
        http_timeout: aiohttp.ClientTimeout,
        channel_id: str,
) -> list[Any]:
    logger.info(f"Fetching {job_type} for channel '{channel_id}':")
    start_time = time.perf_counter()
    url = f'{job_type.value['url']}?channelId={channel_id}'
    logger.info(url)
    all_fids = []

    json_element = (
        "users" if job_type == JobType.followers
        else "members" if job_type == JobType.members
        else None
    )
    acceptable_types = ['application/json', 'text/javascript', 'text/plain']
    ctr = 1  # track number of API calls for a single channel
    retries = 0
    next_url = url
    while True:
        try:
            async with http_conn_pool.get(next_url, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }, timeout=http_timeout) as response:
                content_type = response.headers.get('Content-Type')
                if any(atype in content_type for atype in acceptable_types):
                    body = await response.json(content_type=None)
                    # body = await response.json()
                    all_fids.extend(body.get('result', {}).get(json_element, []))
                    if body.get('next', {}).get('cursor', None):
                        cursor = body['next']['cursor']
                        next_url = f"{url}&cursor={cursor}"
                        ctr += 1
                        if settings.IS_TEST and ctr > settings.TEST_CURSOR_LIMIT:
                            logger.warning(f"Test Environment. Breaking out of loop after {ctr - 1} api calls.")
                            break
                        logger.info(f"sleeping for {settings.WARPCAST_SLEEP_SECS}s")
                        time.sleep(settings.WARPCAST_SLEEP_SECS)
                        logger.info(f"{ctr}: {next_url}")
                        continue
                    else:
                        break
                else:
                    if retries < 3:
                        retries += 1
                        logger.info(f"sleeping for {settings.WARPCAST_SLEEP_SECS}s")
                        time.sleep(settings.WARPCAST_SLEEP_SECS)
                        logger.info(f"retry #{retries} for {ctr}: {next_url}")
                        continue
                    else:
                        raise ValueError('Content-Type for JSON response not acceptable')
        except asyncio.TimeoutError as e:
            logger.error(f"{next_url} - {url} timed out: {e}")
            raise e
        except aiohttp.InvalidURL as e:
            logger.error(f"bad url {next_url} - {url}: {e}")
            raise e
        except aiohttp.ClientError as e:
            logger.error(f"error {next_url} - {url}: {e}")
            raise e
        except Exception as e:
            logger.error(f"error {next_url} - {url}: {e}")
            raise e
    logger.info(
        f"Fetching {job_type} for channel '{channel_id}' took {time.perf_counter() - start_time} secs for {len(all_fids)} fids")
    logger.info(f"First 10 {job_type} for channel '{channel_id}': {all_fids[:10]}")
    return all_fids

async def process_channel(
        job_type: JobType,
        job_time: datetime.datetime,
        db_pool: Pool,
        http_conn_pool: aiohttp.ClientSession,
        http_timeout: aiohttp.ClientTimeout,
        channel_id: str,
):
    try:
        fids = await fetch_channel_fids(job_type,http_conn_pool, http_timeout, channel_id)
        if job_type == JobType.followers:
            rows = [tuple([follower['fid'], follower['followedAt'], job_time, channel_id]) for follower in fids]
        elif job_type == JobType.members:
            rows = [tuple([member['fid'], member['memberAt'], job_time, channel_id]) for member in fids]

        sample_size = min(10, len(rows))
        sample = random.sample(rows, sample_size)
        logger.info(f"Sample of {sample_size} rows for channel '{channel_id}': {sample}")

        await insert_db(job_type, db_pool, rows, channel_id)
    except Exception as e:
        logger.error(f"Error processing channel '{channel_id}': {e}")
        raise e

    return channel_id


async def insert_db(
        job_type: JobType,
        db_pool: Pool,
        rows: list,
        channel_id: str,
):
    logger.info(f"Inserting {len(rows)} rows for channel '{channel_id}'")
    NEW_TBL = f"{job_type.value['live_table']}_new"
    column_names = job_type.value['columns']
    logger.info(f"Inserting {len(rows)} rows for channel '{channel_id}' into {NEW_TBL} with columns {column_names}")
    start_time = time.perf_counter()

    async with db_pool.acquire() as connection:
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                try:
                    await connection.copy_records_to_table(
                        NEW_TBL,
                        records=rows,
                        columns=column_names,
                        timeout=settings.POSTGRES_TIMEOUT_SECS,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to insert {len(rows)} records for channel '{channel_id}'"
                    )
                    logger.error(f"{e}")
                    raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs to insert {len(rows)} rows")

def prepare_db(
        pg_dsn: str, 
        timeout_ms: int,
        job_type: JobType,
):
    LIVE_TBL = job_type.value['live_table']
    NEW_TBL = f"{LIVE_TBL}_new"
    logger.info(f"Prepping '{NEW_TBL}'")
    start_time = time.perf_counter()
    create_sql = (
        f"DROP TABLE IF EXISTS {NEW_TBL};"
        f"CREATE TABLE {NEW_TBL} (LIKE {LIVE_TBL} INCLUDING ALL);"
    )
    logger.debug(f"Executing: {create_sql}")
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {create_sql}")
                cursor.execute(create_sql)
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

def replace_db(
        pg_dsn: str, 
        timeout_ms: int,
        job_type: JobType,
):
    LIVE_TBL = job_type.value['live_table']
    NEW_TBL = f"{LIVE_TBL}_new"
    OLD_TBL = f"{LIVE_TBL}_old"
    logger.info(f"Swapping {LIVE_TBL} to {OLD_TBL} and {NEW_TBL} to {LIVE_TBL}")
    start_time = time.perf_counter()
    replace_sql = (
        f"DROP TABLE IF EXISTS {OLD_TBL};"
        f"ALTER TABLE {LIVE_TBL} RENAME TO {OLD_TBL};"
        f"ALTER TABLE {NEW_TBL} RENAME TO {LIVE_TBL};"
    )
    logger.debug(f"Executing: {replace_sql}")
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {replace_sql}")
                cursor.execute(replace_sql)
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

def merge_db(
        pg_dsn: str, 
        short_timeout_ms: int,
        long_timeout_ms: int,
        job_type: JobType,
):
    LIVE_TBL = job_type.value['live_table']
    NEW_TBL = f"{LIVE_TBL}_new"
    WIP_TBL = f"{LIVE_TBL}_wip"
    logger.info(f"Deleting previous rows for table '{LIVE_TBL}'")
    start_time = time.perf_counter()
    wip_sql = (
        f"DROP TABLE IF EXISTS {WIP_TBL};"
        f"CREATE TABLE {WIP_TBL} (LIKE {LIVE_TBL} INCLUDING ALL);"
    )
    insert_sql = f"""
        WITH live_channels AS (
            SELECT distinct channel_id
            FROM {LIVE_TBL}
        ),
        new_channels AS (
            SELECT distinct channel_id
            FROM {NEW_TBL}
        ),
        missing_live_channels AS (
            SELECT live_channels.channel_id
            FROM live_channels
            LEFT JOIN new_channels
                ON (live_channels.channel_id = new_channels.channel_id)
            WHERE new_channels.channel_id is NULL
        )
        INSERT INTO {NEW_TBL}
        SELECT fid, followedat, insert_ts, live.channel_id as channel_id
        FROM {LIVE_TBL} as live
        INNER JOIN missing_live_channels ON
        (missing_live_channels.channel_id = live.channel_id)
    """
    replace_sql = (
        f"DROP TABLE IF EXISTS {LIVE_TBL};"
        f"ALTER TABLE {NEW_TBL} RENAME TO {LIVE_TBL};"
    )
    try:
        # transaction scope begins
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={long_timeout_ms}"
            )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {wip_sql}")
                cursor.execute(wip_sql)
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Inserted rows: {cursor.rowcount}")
        # transaction scope ends
        # transaction scope begins
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={short_timeout_ms}"
            )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {replace_sql}")
                cursor.execute(replace_sql)
        # transaction scope ends
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

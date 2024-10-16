from enum import Enum
import random
import time
import asyncio
from typing import Any
import datetime

from config import settings

from loguru import logger
import aiohttp
from asyncpg.pool import Pool

class JobType(Enum):
    followers = ('https://api.warpcast.com/v1/channel-followers','warpcast_followers')
    members = ('https://api.warpcast.com/fc/channel-members','warpcast_members')

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
    url = f'{job_type.value[0]}?channelId={channel_id}'
    logger.info(url)
    all_fids = []

    json_element = (
        "users" if job_type == JobType.followers
        else "members" if job_type == JobType.members
        else None
    )
    ctr = 1  # track number of API calls for a single channel
    next_url = url
    while True:
        try:
            async with http_conn_pool.get(next_url, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }, timeout=http_timeout) as response:
                body = await response.json()
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
                else:
                    break
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
    table_name = job_type.value[1]
    column_names = (
        ["fid", "followedat", "insert_ts", "channel_id"] if job_type == JobType.followers
        else ["fid", "memberat", "insert_ts", "channel_id"] if job_type == JobType.members
        else []
    )
    logger.info(f"Inserting {len(rows)} rows for channel '{channel_id}' into {table_name} with columns {column_names}")
    start_time = time.perf_counter()

    async with db_pool.acquire() as connection:
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                try:
                    await connection.copy_records_to_table(
                        table_name,
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

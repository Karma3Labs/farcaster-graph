import time
import asyncio
from typing import Any
import datetime

from config import settings

from loguru import logger
import aiohttp
from asyncpg.pool import Pool
import pandas as pd


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

async def fetch_channel_followers(
    http_conn_pool: aiohttp.ClientSession,
    http_timeout: aiohttp.ClientTimeout,
    channel_id: str,
) -> list[Any]:
    logger.info(f"Fetching followers for channel '{channel_id}':")
    start_time = time.perf_counter()
    url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
    logger.info(url)
    all_followers = []

    ctr = 1  # track number of API calls for a single channel
    next_url = url
    while True:
        try:
            async with http_conn_pool.get(next_url, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }, timeout=http_timeout) as response:
                body = await response.json()
                all_followers.extend(body.get('result', {}).get('users', []))
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
    logger.info(f"Fetching followers for channel '{channel_id}' took {time.perf_counter() - start_time} secs for {len(all_followers)} fids")
    logger.info(f"First 10 followers for channel '{channel_id}': {all_followers[:10]}")
    return all_followers

async def process_channel(
    job_time: datetime.datetime,
    db_pool: Pool,
    http_conn_pool: aiohttp.ClientSession,
    http_timeout: aiohttp.ClientTimeout,
    channel_id: str,
):
    followers = await fetch_channel_followers(http_conn_pool, http_timeout, channel_id)
    rows = [tuple([follower['fid'], follower['followedAt'], job_time, channel_id]) for follower in followers]
    # WARNING: warpcast returns duplicates. So, I have dropped the unique constraint on db. 
    # logger.info(f"before de-dup {len(followers)} followers for channel '{channel_id}'")
    # rows = list(set(rows))
    # logger.info(f"after de-dup {len(followers)} followers for channel '{channel_id}'")
    start_time = time.perf_counter()
    # Take a connection from the pool.
    async with db_pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                try:
                    await connection.copy_records_to_table(
                        "warpcast_followers",
                        records=rows,
                        columns=["fid", "followedat", "insert_ts", "channel_id"],
                        timeout=settings.POSTGRES_TIMEOUT_SECS,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to insert {len(followers)} followers for channel '{channel_id}'"
                    )
                    logger.error(f"{e}")
                    return 
    logger.info(f"db took {time.perf_counter() - start_time} secs to insert {len(followers)} rows")
    return channel_id
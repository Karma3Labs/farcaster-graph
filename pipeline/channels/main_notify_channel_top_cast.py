# standard dependencies
import argparse
import asyncio
import sys
from itertools import batched
import json

import niquests
import asyncpg

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from urllib3.util import Retry

import cura_utils

# local dependencies
from config import settings

# Configure logger
logger.remove()
level_per_module = {"": settings.LOG_LEVEL, "silentlib": False}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)

load_dotenv()


async def fetch_active_channels(pg_dsn: str) -> list[str]:
    """
    Fetch channels that had casts in the last 24 hours
    """
    pool = await asyncpg.create_pool(pg_dsn, min_size=1, max_size=5)
    
    sql = """
    SELECT DISTINCT parent_url
    FROM neynarv3.casts
    WHERE 
        parent_url IS NOT NULL 
        AND "timestamp" >= NOW() - INTERVAL '24 hours'
    """
    
    if settings.IS_TEST:
        sql = f"{sql} LIMIT 5"
    
    logger.info(f"Executing query: {sql}")
    
    async with pool.acquire() as connection:
        async with connection.transaction():
            try:
                rows = await connection.fetch(sql, timeout=settings.POSTGRES_TIMEOUT_SECS)
                parent_urls = [row['parent_url'] for row in rows]
                logger.info(f"Found {len(parent_urls)} active channels in last 24 hours")
                logger.debug(f"Active channels: {parent_urls[:10] if len(parent_urls) > 10 else parent_urls}")
                return parent_urls
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                return []
            finally:
                await pool.close()


def lookup_channel_ids(session: niquests.Session, parent_urls: list[str], timeouts: tuple) -> dict[str, str]:
    """
    Use Neynar API to convert parent URLs to channel IDs
    """
    channel_mapping = {}
    
    # Neynar bulk channel lookup API
    url = "https://api.neynar.com/v2/farcaster/channel/bulk"
    headers = {
        "Accept": "application/json",
        "x-api-key": settings.NEYNAR_API_KEY,
    }
    
    # Process in batches of 100 (Neynar API limit)
    for batch in batched(parent_urls, 100):
        params = {"urls": ",".join(batch)}
        
        try:
            logger.debug(f"Looking up channel IDs for batch: {batch}")
            response = session.get(url, params=params, headers=headers, timeout=timeouts)
            
            if response.status_code == 200:
                data = response.json()
                channels = data.get("channels", [])
                
                for channel in channels:
                    parent_url = channel.get("parent_url")
                    channel_id = channel.get("id")
                    if parent_url and channel_id:
                        channel_mapping[parent_url] = channel_id
                        
                logger.info(f"Successfully mapped {len(channels)} channels in batch")
            else:
                logger.error(f"Neynar API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error calling Neynar API: {e}")
            continue
    
    logger.info(f"Total channel mappings: {len(channel_mapping)}")
    return channel_mapping


def get_top_cast(session: niquests.Session, channel_id: str, timeouts: tuple) -> dict:
    """
    Get the top cast for a channel from K3L API
    """
    url = f"https://graph.cast.k3l.io/channels/casts/top/{channel_id}"
    
    try:
        logger.debug(f"Getting top cast for channel: {channel_id}")
        response = session.get(url, timeout=timeouts)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                top_cast = data[0]  # Get the first (top) cast
                logger.debug(f"Top cast for {channel_id}: {top_cast.get('hash', 'N/A')}")
                return top_cast
            else:
                logger.warning(f"No top casts found for channel {channel_id}")
                return None
        else:
            logger.error(f"K3L API error for {channel_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting top cast for {channel_id}: {e}")
        return None


def get_channel_members(session: niquests.Session, channel_id: str, timeouts: tuple) -> list[int]:
    """
    Get channel members from Neynar API
    """
    url = f"https://api.neynar.com/v2/farcaster/channel/members"
    headers = {
        "Accept": "application/json", 
        "x-api-key": settings.NEYNAR_API_KEY,
    }
    
    params = {
        "id": channel_id,
        "limit": 1000  # Max limit
    }
    
    all_members = []
    cursor = None
    
    try:
        while True:
            if cursor:
                params["cursor"] = cursor
            
            logger.debug(f"Getting members for channel: {channel_id}")
            response = session.get(url, params=params, headers=headers, timeout=timeouts)
            
            if response.status_code == 200:
                data = response.json()
                members = data.get("members", [])
                
                # Extract FIDs
                fids = [member.get("user", {}).get("fid") for member in members if member.get("user", {}).get("fid")]
                all_members.extend(fids)
                
                # Check for pagination
                next_cursor = data.get("next", {}).get("cursor")
                if next_cursor:
                    cursor = next_cursor
                    logger.debug(f"Found more members, continuing with cursor: {cursor}")
                else:
                    break
                    
            else:
                logger.error(f"Neynar members API error for {channel_id}: {response.status_code} - {response.text}")
                break
                
    except Exception as e:
        logger.error(f"Error getting members for {channel_id}: {e}")
    
    logger.info(f"Found {len(all_members)} members for channel {channel_id}")
    return all_members


async def notify():
    """
    Main notification function
    """
    pg_dsn = settings.ALT_POSTGRES_ASYNC_URI.get_secret_value()
    
    # Fetch active channels
    parent_urls = await fetch_active_channels(pg_dsn)
    if not parent_urls:
        logger.warning("No active channels found, exiting")
        return
    
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    
    with niquests.Session(retries=retries) as session:
        timeouts = (connect_timeout_s, read_timeout_s)
        
        # Convert parent URLs to channel IDs
        channel_mapping = lookup_channel_ids(session, parent_urls, timeouts)
        if not channel_mapping:
            logger.warning("No channel mappings found, exiting")
            return
        
        # Process each channel
        for parent_url, channel_id in channel_mapping.items():
            logger.info(f"Processing channel: {channel_id} ({parent_url})")
            
            # Get top cast
            top_cast = get_top_cast(session, channel_id, timeouts)
            if not top_cast:
                logger.warning(f"No top cast found for {channel_id}, skipping")
                continue
            
            # Get channel members
            member_fids = get_channel_members(session, channel_id, timeouts)
            if not member_fids:
                logger.warning(f"No members found for {channel_id}, skipping")
                continue
            
            # Send notifications in batches
            if settings.IS_TEST:
                # Limit to small test set
                member_fids = member_fids[:10]
            
            chunk_size = settings.CURA_NOTIFY_CHUNK_SIZE if hasattr(settings, 'CURA_NOTIFY_CHUNK_SIZE') else 100
            
            for batch_fids in batched(member_fids, chunk_size):
                batch_fids = list(batch_fids)
                logger.info(f"Sending top cast notification for channel {channel_id} to {len(batch_fids)} members")
                
                # Send notification using cura_utils
                cura_utils.top_cast_notify(
                    session=session,
                    timeouts=timeouts,
                    channel_id=channel_id,
                    fids=batch_fids,
                    cast_hash=top_cast.get("hash"),
                    cast_text=top_cast.get("text", "")[:100],  # Truncate for notification
                )
            
            logger.info(f"Completed notifications for channel {channel_id}")
    
    logger.info("All notifications completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="store_true",
        help="dummy arg to prevent accidental execution",
        required=True,
    )
    parser.add_argument("--dry-run", help="indicate dry-run mode", action="store_true")
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.dry_run:
        settings.IS_TEST = True

    asyncio.run(notify())
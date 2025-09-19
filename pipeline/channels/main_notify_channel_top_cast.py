# standard dependencies
import uuid
import argparse
import asyncio
import sys
from itertools import batched
import json
from collections import defaultdict

import niquests
import asyncpg

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from urllib3.util import Retry

import cura_utils

# local dependencies
from config import settings
from . import channel_db_utils, neynar_db_utils
from fcm.webhook_sync import get_mobile_app_user_fids

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


def lookup_channel_ids(
    session: niquests.Session, parent_urls: list[str], timeouts: tuple
) -> dict[str, str]:
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
        params = {"ids": ",".join(batch), "type": "parent_url"}

        try:
            logger.debug(f"Looking up channel IDs for batch: {batch}")
            response = session.get(
                url, params=params, headers=headers, timeout=timeouts
            )

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
                logger.error(
                    f"Neynar API error: {response.status_code} - {response.text}"
                )

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
            data = response.json()["result"]
            if isinstance(data, list) and len(data) > 0:
                top_cast = data[0]  # Get the first (top) cast
                logger.debug(
                    f"Top cast for {channel_id}: {top_cast.get('hash', 'N/A')}"
                )
                return top_cast
            else:
                logger.warning(f"No top casts found for channel {channel_id}")
                return None
        else:
            logger.error(
                f"K3L API error for {channel_id}: {response.status_code} - {response.text}"
            )
            return None

    except Exception as e:
        logger.error(f"Error getting top cast for {channel_id}: {e}")
        return None


def get_channel_members(
    session: niquests.Session, channel_id: str, timeouts: tuple
) -> list[int]:
    """
    Get channel members from Neynar API
    """
    url = f"https://api.neynar.com/v2/farcaster/channel/member/list"
    headers = {
        "Accept": "application/json",
        "x-api-key": settings.NEYNAR_API_KEY,
    }

    params = {"channel_id": channel_id, "limit": 100}  # Max limit

    all_members = []
    cursor = None

    try:
        while True:
            if cursor:
                params["cursor"] = cursor

            logger.debug(f"Getting members for channel: {channel_id}")
            response = session.get(
                url, params=params, headers=headers, timeout=timeouts
            )

            if response.status_code == 200:
                data = response.json()
                members = data.get("members", [])

                # Extract FIDs
                fids = [
                    member.get("user", {}).get("fid")
                    for member in members
                    if member.get("user", {}).get("fid")
                ]
                all_members.extend(fids)

                # Check for pagination
                next_cursor = data.get("next", {}).get("cursor")
                if next_cursor:
                    cursor = next_cursor
                    logger.debug(
                        f"Found more members, continuing with cursor: {cursor}"
                    )
                else:
                    break

            else:
                logger.error(
                    f"Neynar members API error for {channel_id}: {response.status_code} - {response.text}"
                )
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

    user_fids = get_mobile_app_user_fids()
    logger.info(f"mobile app user fids: {len(user_fids)}")

    users_to_notify_by_channel_id = defaultdict(list)
    for fid in user_fids:
        top_channels = await channel_db_utils.get_top_channels_for_fid(
            logger, pg_dsn, fid
        )
        if not top_channels:
            logger.warning(f"No top channels found for {fid}, skipping")
            continue
        top_channel = top_channels[0]["channel_id"]
        logger.info(f"fid: {fid},  top channel: {top_channel}")
        users_to_notify_by_channel_id[top_channel].append(fid)

    logger.info("Fetched top channels for all users")

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0

    with niquests.Session(retries=retries) as session:
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)

        for channel_id, fids_to_notify in users_to_notify_by_channel_id.items():
            # Process each channel
            logger.info(f"Processing channel: {channel_id} ({fids_to_notify})")

            # Get top cast
            top_cast = get_top_cast(session, channel_id, timeouts)
            if not top_cast:
                logger.warning(f"No top cast found for {channel_id}, skipping")
                continue

            top_casts = await neynar_db_utils.get_cast_content(
                logger, pg_dsn, top_cast["cast_hash"]
            )
            if not top_casts:
                logger.warning(
                    f"No cast text found for {top_cast['cast_hash']}, skipping"
                )
                continue

            top_cast_content = top_casts[0]["text"]
            top_cast_author_fid = top_casts[0]["fid"]

            profile_details = await neynar_db_utils.get_profile_details(
                logger, pg_dsn, [top_cast_author_fid]
            )
            if not profile_details:
                logger.warning(
                    f"No profile details found for {fids_to_notify}, skipping"
                )
                continue

            top_cast_author_display_name = profile_details[top_cast_author_fid][
                "display_name"
            ]

            # for fid, profile in profile_details.items():
            # display_name = profile["display_name"]
            title = f"{top_cast_author_display_name}'s top cast in /{channel_id}"
            body = top_cast_content

            notification_id = uuid.uuid4()
            return cura_utils.notify(
                session,
                timeouts,
                channel_id,
                fids_to_notify,
                notification_id,
                title,
                body,
                target_url=f"https://cura.network/{channel_id}?t=top",
                target_client="mobile",
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

# standard dependencies
import datetime
import hashlib
import urllib.parse
import uuid
from enum import StrEnum
from typing import Optional

import niquests
import pandas as pd
import pytz

# 3rd party dependencies
from loguru import logger
from urllib3.util import Retry

import utils

# local dependencies
from config import settings


class ScreenName(StrEnum):
    # feed, leaderboard, token, details
    WEEKLY_MODS = "details"
    TOKENS = "token"
    LEADERBOARD = "leaderboard"
    DAILY_CAST = "feed"


def leaderboard_notify(
    session: niquests.Session,
    timeouts: tuple,
    channel_id: str,
    is_token: bool,
    fids: list[int],
    cutoff_time: datetime.datetime,
):
    notification_id = hashlib.sha256(
        f"{channel_id}-{cutoff_time}".encode("utf-8")
    ).hexdigest()
    logger.info(f"Sending notification for channel {channel_id}-{cutoff_time}")
    title = f"/{channel_id} leaderboard updated!"
    if is_token:
        body = f"Claim your /{channel_id} tokens!"
        screen_name = ScreenName.TOKENS.value
    else:
        body = f"Check your /{channel_id} rank!"
        screen_name = ScreenName.LEADERBOARD.value
    return notify(
        session, timeouts, channel_id, fids, notification_id, title, body, screen_name
    )


def daily_cast_notify(
    session: niquests.Session,
    timeouts: tuple,
    channel_id: str,
    fids: list[int],
):
    pacific_tz = pytz.timezone("US/Pacific")
    # hash is based on day so we don't risk sending out more than one notification
    pacific_9am_str = datetime.datetime.now(pacific_tz).strftime("%Y-%m-%d")
    notification_id = hashlib.sha256(
        f"{channel_id}-{pacific_9am_str}".encode("utf-8")
    ).hexdigest()
    logger.info(f"Sending notification for channel {channel_id}-{pacific_9am_str}")
    title = f"What's trending on /{channel_id} ?"
    body = f"See what you missed in /{channel_id} in the last 24 hours"
    screen_name = ScreenName.DAILY_CAST.value
    return notify(
        session, timeouts, channel_id, fids, notification_id, title, body, screen_name
    )


def weekly_mods_notify(
    session: niquests.Session,
    timeouts: tuple,
    channel_id: str,
    fids: list[int],
):
    current_week = utils.dow_utc_time(utils.DOW.WEDNESDAY)
    notification_id = hashlib.sha256(
        f"{channel_id}-{current_week}".encode("utf-8")
    ).hexdigest()
    logger.info(f"Sending notification for channel {channel_id}-{current_week}")
    title = f"Check out your /{channel_id} stats"
    body = "Your top casts and members stats are in, tap to look."
    return notify(
        session,
        timeouts,
        channel_id,
        fids,
        notification_id,
        title,
        body,
        target_url=f"https://cura.network/{channel_id}/moderation/stats",
    )


def notify(
    session: niquests.Session,
    timeouts: tuple,
    channel_id: Optional[str],
    fids: list[int],
    notification_id: str,
    title: str,
    body: str,
    screen_name: str = "",
    target_url: Optional[str] = None,
    target_client: str = "all",
    notification_type: str = "generic",
):
    req = {
        "title": title,
        "body": body,
        "notificationId": notification_id,
        "channel_id": channel_id,
        "fids": fids,
        "screen": screen_name,
        "target_client": target_client,
    }
    if target_url:
        req["target_url"] = target_url

    url = "https://notifications.cura.network/api/v1/notify"
    logger.info(f"{url}: {req}")
    if settings.IS_TEST:
        logger.warning(f"Skipping notifications for channel {channel_id} in test mode")
        logger.warning(f"Test Mode: skipping notifications for fids {fids} ")
        return
    response = session.post(url, json=req, timeout=timeouts)
    res_json = response.json()
    if response.status_code != 200:
        logger.error(f"Failed to send notification: {res_json}")
        raise Exception(f"Failed to send notification: {res_json}")
    else:
        logger.info(f"Notification sent: {res_json}")
    return


def fetch_channel_hide_list() -> pd.DataFrame:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    df = pd.DataFrame()
    with niquests.Session(retries=retries) as session:
        # reuse TCP connection for multiple scm requests
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)
        url = urllib.parse.urljoin(
            settings.CURA_FE_API_URL, "/api/internal/channel-hide-list"
        )
        logger.info(f"url: {url}")
        # TODO parallelize this
        response = session.post(url, json={}, timeout=timeouts)
        res_json = response.json()
        if response.status_code != 200:
            logger.error(f"Failed to fetch channel-hide-list: {res_json}")
            raise Exception(f"Failed to fetch channel-hide-list: {res_json}")
        else:
            logger.trace(f"channel-hide-list: {res_json}")
            # Read the response content into a pandas DataFrame
            data = pd.DataFrame.from_records(res_json.get("data"))
            print(len(data))
            df = pd.concat([df, data], axis=0)
    return df


def fetch_frame_users() -> list[int]:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    with niquests.Session(retries=retries) as session:
        # reuse TCP connection for multiple scm requests
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CURA_FE_API_KEY}",
            }
        )
        timeouts = (connect_timeout_s, read_timeout_s)
        url = urllib.parse.urljoin(
            settings.CURA_FE_API_URL, "/api/internal/warpcast-frame-users"
        )
        logger.info(f"url: {url}")
        response = session.post(url, json={}, timeout=timeouts)
        res_json = response.json()
        if response.status_code != 200:
            logger.error(f"Failed to fetch warpcast-frame-users: {res_json}")
            raise Exception(f"Failed to fetch warpcast-frame-users: {res_json}")
        else:
            logger.trace(f"warpcast-frame-users: {res_json}")
            fids = res_json.get("data")
            print(len(fids))
    return fids

import io
import urllib.parse

import niquests
import pandas as pd
import psutil
from loguru import logger
from niquests.auth import HTTPBasicAuth
from urllib3.util import Retry

from .config import settings


def log_memusage(l):
    mem_usage = psutil.virtual_memory()
    l.info(f"Total: {mem_usage.total / (1024 ** 2):.2f}M")
    l.info(f"Used: {mem_usage.percent}%")
    l.info(f"Used: {mem_usage.used / (1024 ** 2):.2f}M")
    l.info(f"Free: {mem_usage.free / (1024 ** 2):.2f}M")


def df_info_to_string(df: pd.DataFrame, with_sample: bool = False):
    buf = io.StringIO()
    df.info(verbose=True, buf=buf, memory_usage="deep", show_counts=True)
    if with_sample:
        buf.write(f"{'-' *15}\n| Sample rows:\n{'-' *15}\n")
        # noinspection PyUnresolvedReferences
        # (sample() has wrong type hint)
        df.sample(5).to_csv(buf, index=False)
    return buf.getvalue()


# TODO this should be async
def fetch_channel(channel_id: str) -> str:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    http_session = niquests.Session(retries=retries)
    url = f"https://api.warpcast.com/v1/channel?channelId={channel_id}"
    logger.info(url)
    response = http_session.get(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=5,
    )
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    data = response.json()["result"]["channel"]
    return data.get("url")


async def fetch_channel_token(channel_id: str) -> dict | None:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 5.0
    path = f"/token/lookupTokenForChannel/{channel_id}"
    async with niquests.AsyncSession(retries=retries) as http_session:
        http_session.auth = HTTPBasicAuth(
            settings.CURA_SCMGR_USERNAME,
            settings.CURA_SCMGR_PASSWORD.get_secret_value(),
        )
        response = await http_session.get(
            urllib.parse.urljoin(settings.CURA_SCMGR_URL, path),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=(connect_timeout_s, read_timeout_s),
        )
        if response.status_code == 200:
            logger.info(f"Channel '{channel_id}' has token.")
            channel_token = response.json()
            return channel_token
        elif response.status_code == 404:
            logger.warning(
                f"404 Error: No tokens for Channel {channel_id} :{response.reason}"
            )
            return None
        else:
            logger.error(f"Server error: {response.status_code}:{response.reason}")
            raise Exception(f"Server error: {response.status_code}:{response.reason}")

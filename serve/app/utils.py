import io

import niquests
from urllib3.util import Retry
from loguru import logger
import psutil
import pandas as pd

def log_memusage(logger:logger):
  mem_usage = psutil.virtual_memory()
  logger.info(f"Total: {mem_usage.total/(1024**2):.2f}M")
  logger.info(f"Used: {mem_usage.percent}%")
  logger.info(f"Used: {mem_usage.used/(1024**2):.2f}M")
  logger.info(f"Free: {mem_usage.free/(1024**2):.2f}M" )

def df_info_to_string(df: pd.DataFrame, with_sample:bool = False):
  buf = io.StringIO()
  df.info(verbose=True, buf=buf, memory_usage="deep", show_counts=True)
  if with_sample:
    buf.write(f"{'-' *15}\n| Sample rows:\n{'-' *15}\n")
    df.sample(5).to_csv(buf, index=False)
  return buf.getvalue()


def fetch_channel(channel_id: str) -> str:
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={'GET'},
    )
    http_session = niquests.Session(retries=retries)
    url = f'https://api.warpcast.com/v1/channel?channelId={channel_id}'
    logger.info(url)
    response = http_session.get(url, headers={
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    },
                                timeout=5)
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    data = response.json()['result']['channel']
    return data.get('url')
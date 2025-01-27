# standard dependencies
import sys
import argparse
import urllib.parse
from urllib3.util import Retry
import hashlib
import datetime

# local dependencies
from config import settings
from . import channel_db_utils
import utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import niquests
import numpy as np
import pandas as pd

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)

load_dotenv()


def cura_notify(session:niquests.Session, timeouts:tuple, channel_id:str, fids: list[int], end_time:datetime.datetime):
    notification_id = hashlib.sha256(f"{channel_id}-{end_time}".encode("utf-8")).hexdigest()
    logger.info(f"Sending notification for channel {channel_id}-{end_time}")
    title = f"/{channel_id} leaderboard updated!"
    body = f"Claim your /{channel_id} tokens!"
    req = {
        "title": title,
        "body": body,
        "notificationId": notification_id,
        "channelId": channel_id,
        "fids": fids.tolist() # convert np array to scalar list
    }
    url = urllib.parse.urljoin(settings.CURA_SCMGR_URL,"/api/warpcast-frame-notify")
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

   
def group_and_chunk_df(
    df: pd.DataFrame, group_by_column: str, collect_column: str, chunk_size: int
) -> pd.DataFrame:
    def chunk_list(x):
        return [list(chunk) for chunk in np.array_split(x, np.ceil(len(x)/chunk_size))]
    
    return df.groupby(group_by_column)[collect_column].agg(list).apply(chunk_list)

def notify():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    (end_time, entries_df) = channel_db_utils.fetch_notify_entries(
        logger, pg_dsn, settings.POSTGRES_TIMEOUT_MS,
    )
    logger.info(f"Channel fids to be notified: {utils.df_info_to_string(entries_df, with_sample=True)}")
    if settings.IS_TEST:
        chunk_size = 2
    else:
        chunk_size = settings.CURA_NOTIFY_CHUNK_SIZE
    chunked_df = group_and_chunk_df(entries_df, "channel_id", "fid", chunk_size)
    logger.info(f"Channel fids to be notified: {utils.df_info_to_string(chunked_df, with_sample=True, head=True)}")

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
        timeouts=(connect_timeout_s, read_timeout_s)
        for channel_id, fids in chunked_df.items():
            for fids_chunk in fids:
                logger.info(f"Sending notification for channel {channel_id}: {fids_chunk}")
                cura_notify(session, timeouts, channel_id, fids_chunk, end_time)
            logger.info(f"Notifications sent for channel '{channel_id}'")
        logger.info("Notifications sent for all channels")    


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="store_true",
        help="dummy arg to prevent accidental execution",
        required=True
    )
    parser.add_argument(
        "--dry-run",
        help="indicate dry-run mode",
        action="store_true"
    ) 
    args = parser.parse_args()
    print(args)
    logger.info(settings)
    
    if args.dry_run:
        settings.IS_TEST = True

    notify()
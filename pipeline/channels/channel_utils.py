# system dependencies
import time

import pandas as pd
# local dependencies
from config import settings
from . import channel_model
from timer import Timer

# 3rd party dependencies
from loguru import logger
import niquests


@Timer(name="fetch_all_channels")
def fetch_all_channels(http_session: niquests.Session) -> list[channel_model.Channel]:
    url = 'https://api.warpcast.com/v2/all-channels'
    response = http_session.get(url, headers={
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    },
                                timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    data = response.json()['result']['channels']
    return [channel_model.Channel(c) for c in data]


@Timer(name="fetch_channel")
def fetch_channel(http_session: niquests.Session, channel_id: str) -> channel_model.Channel:
    url = f'https://api.warpcast.com/v1/channel?channelId={channel_id}'
    logger.info(url)
    response = http_session.get(url, headers={
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    },
                                timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    data = response.json()['result']['channel']
    return channel_model.Channel(data)


@Timer(name="fetch_channel_followers")
def fetch_channel_followers(http_session: niquests.Session, channel_id: str) -> list[int]:
    url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
    logger.info(url)
    fids = []

    ctr = 1  # track number of API calls for a single channel
    next_url = url
    while True:
        response = http_session.get(next_url, headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
                                    timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"{ctr} Server error: {response.status_code}:{response.reason}")
            raise Exception(f"{ctr} Server error: {response.status_code}:{response.reason}")
        body = response.json()
        logger.info(f"{len(body['result']['fids'])} fids fetched")
        fids.extend(body['result']['fids'])
        if 'next' in body and 'cursor' in body['next'] and body['next']['cursor']:
            cursor = body['next']['cursor']
            next_url = f"{url}&cursor={cursor}"
            ctr += 1
            if settings.IS_TEST and ctr > 3:
                logger.warning(f"Test Environment. Breaking out of loop after {ctr - 1} api calls.")
                break
            time.sleep(settings.CHANNEL_SLEEP_SECS)
            logger.info(f"{ctr}: {next_url}")
        else:
            break
    return fids


def get_seed_fids_from_csv(csv_path):
    """
    Read the csv.
    Rename the columns and select only relevant columns.
    Create the list of fids
    """
    seeds_df = pd.read_csv(csv_path)
    seeds_df.rename(columns={"Unnamed: 1": "seed_peers"}, inplace=True)
    seeds_df = seeds_df.iloc[1:len(seeds_df)][["channel id", "seed_peers"]]
    seeds_df["seed_fids_list"] = seeds_df.apply(lambda row: row["seed_peers"].split(","), axis=1)
    seeds_df['channel id'] = seeds_df['channel id'].str.lower()
    return seeds_df

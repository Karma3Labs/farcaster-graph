# standard dependencies
import sys
import time
from random import sample
import asyncio

import aiohttp
import requests

# local dependencies
from config import settings
from . import channel_db_utils
from . import channel_model
from timer import Timer

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

import json
from types import SimpleNamespace

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

def fetch_all_channels() -> list[channel_model.Channel]:
  url = 'https://api.warpcast.com/v2/all-channels'
  response = requests.get(url,headers = {
                              'Accept': 'application/json',
                              'Content-Type': 'application/json'
                              },
                          timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
  if response.status_code != 200:
      logger.error(f"Server error: {response.status_code}:{response.reason}")
      raise Exception(f"Server error: {response.status_code}:{response.reason}")
  data = response.json()['result']['channels']
  return [channel_model.Channel(c) for c in data]

def fetch_channel_followers(channel_id: str) -> list[int]:
  url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
  print(url)
  fids = []

  next_url = url
  while True:
    response = requests.get(next_url,headers = {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json'
                                },
                            timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    body = response.json()
    fids.extend(body['result']['fids'])
    if 'next' in body and 'cursor' in body['next'] and body['next']['cursor']:
      cursor = body['next']['cursor']
      next_url = f"{url}&cursor={cursor}"
      print(next_url)
    else:
      break
  return fids

async def main():
  pg_dsn = settings.POSTGRES_DSN.get_secret_value()

  channels = fetch_all_channels()

  # channel_db_utils.upsert_channels(logger, pg_dsn, channels)
  # logger.info(f"inserted {len(channels)} channels to db")
  # logger.info(f"Sample channels: {sample(channels, min(3, len(channels)))}")

  for c in channels:
    fids = fetch_channel_followers(c.id)
    channel_db_utils.insert_channel_follows(logger, pg_dsn, c.id, fids)

  #{'id': 'electronic', 'url': 'chain://eip155:1/erc721:0x05acde54e82e7e38ec12c5b5b4b1fd1c8d32658d', 'name': 'Electronic Music', 'description': 'Electronic music from around the world, below and under the ground.', 'imageUrl': 'https://i.seadn.io/gcs/files/92b324400baa286b6b4791b0371ad83e.png?auto=format&dpr=1&w=256', 'leadFid': 2, 'hostFids': [2, 5851], 'createdAt': 1689888729, 'followerCount': 5062}



if __name__ == "__main__":
  # TODO don't depend on current directory to find .env
  load_dotenv()
  print(settings)

  logger.debug('hello main')
  asyncio.run(main())
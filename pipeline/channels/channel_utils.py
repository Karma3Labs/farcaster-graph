# local dependencies
from config import settings
from . import channel_model
from timer import Timer

# 3rd party dependencies
from loguru import logger
import niquests as requests

@Timer(name="fetch_all_channels")
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

@Timer(name="fetch_channel")
def fetch_channel(channel_id: str) -> channel_model.Channel:
  url = f'https://api.warpcast.com/v1/channel?channelId={channel_id}'
  logger.info(url)
  response = requests.get(url,headers = {
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
def fetch_channel_followers(channel_id: str) -> list[int]:
  url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
  logger.info(url)
  fids = []

  ctr = 1 # track number of API calls for a single channel
  next_url = url
  while True:
    response = requests.get(next_url, headers = {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json'
                                },
                            timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
    if response.status_code != 200:
        logger.error(f"{ctr} Server error: {response.status_code}:{response.reason}")
        raise Exception(f"{ctr} Server error: {response.status_code}:{response.reason}")
    body = response.json()
    fids.extend(body['result']['fids'])
    if 'next' in body and 'cursor' in body['next'] and body['next']['cursor']:
      cursor = body['next']['cursor']
      next_url = f"{url}&cursor={cursor}"
      ctr += 1
      if settings.IS_TEST and ctr > 3:
        logger.warning(f"Test Environment. Breaking out of loop after {ctr-1} api calls.")
        break
      logger.info(f"{ctr}: {url}")
    else:
      break
  return fids



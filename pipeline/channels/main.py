# standard dependencies
import sys
import argparse
import asyncio
import random
from pathlib import Path

# local dependencies
from config import settings
from . import channel_model
import utils
from . import go_eigentrust

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import niquests as requests
import pandas

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


def fetch_channel_followers(channel_id: str) -> list[int]:
  url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
  logger.info(url)
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
      logger.info(next_url)
    else:
      break
  return fids

async def main(localtrust_pkl: Path, channel_ids: list[str]):
  # load localtrust
  utils.log_memusage(logger)
  logger.info(f"loading {localtrust_pkl}")
  global_lt_df = pandas.read_pickle(localtrust_pkl)
  logger.info(utils.df_info_to_string(global_lt_df, with_sample=True))
  utils.log_memusage(logger)

  # for each channel, take a slice of localtrust and run go-eigentrust
  for cid in channel_ids:
    channel = fetch_channel(channel_id=cid)
    fids = fetch_channel_followers(channel_id=cid)

    logger.info(f"Channel details: {channel}")
    logger.info(f"Number of channel followers: {len(fids)}")
    logger.info(f"Sample of channel followers: {random.sample(fids, 5)}")

    channel_lt_df = global_lt_df[global_lt_df['i'].isin(fids) & global_lt_df['j'].isin(fids)]

    pt_len = len(channel.host_fids)
    pretrust = [{'i': id, 'v': 1/pt_len} for id in channel.host_fids]
    max_pt_id = max(channel.host_fids)
    
    localtrust = channel_lt_df.to_dict(orient="records")
    max_lt_id = max(channel_lt_df['i'].max(), channel_lt_df['j'].max())

    globaltrust = go_eigentrust.go_eigentrust(logger, 
                                              pretrust,
                                              max_pt_id,
                                              localtrust,
                                              max_lt_id
                                              )
    logger.info(f"go_eigentrust returned {len(globaltrust)} entries")
    utils.log_memusage(logger)

    # rename i and v to fid and score respectively
    fid_scores = [ {'fid': score['i'], 'score': score['v']} for score in globaltrust]



if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--ids",
                  nargs='+',
                  help="list of channel ids",
                  required=True)
  parser.add_argument("-l", "--localtrust",
                    help="input localtrust pkl file",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())  

  args = parser.parse_args()
  print(args)

  load_dotenv()
  print(settings)

  logger.debug('hello main')
  # asyncio.run(main(localtrust_pkl=args.localtrust, channel_ids=args.ids))
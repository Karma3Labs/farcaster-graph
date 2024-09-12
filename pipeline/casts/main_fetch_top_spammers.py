# standard dependencies
import sys
import argparse
from random import sample
import asyncio
from io import StringIO
import json

# local dependencies
from config import settings
from timer import Timer
from . import cast_db_utils
from datetime import datetime, timedelta

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import requests
import pandas as pd

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

async def main(filename: str):
  pg_dsn = settings.POSTGRES_ASYNC_URI.get_secret_value()

  now =  datetime.now()
  thirty_days_ago = now - timedelta(days=30)

  rows = await cast_db_utils.fetch_top_spammers(logger,
                                        pg_dsn, start_date=thirty_days_ago, end_date=now)
  top_spammers = []
  for s in rows:
    row = {
      'fid': int(s['fid']),
      'display_name': str(s['display_name']),
      'total_outgoing': int(s['total_outgoing']),
      'spammer_score': float(s['spammer_score']) if s['spammer_score'] else 0.0,
      'total_parent_casts': int(s['total_parent_casts']),
      'total_replies_with_parent_hash': int(s['total_replies_with_parent_hash']),
      'global_openrank_score': float(s['global_openrank_score']) if s['global_openrank_score'] else 0.0,
      'global_rank': int(s['global_rank']) if s['global_rank'] else 0,
      'total_global_rank_rows': int(s['total_global_rank_rows']) if s['total_global_rank_rows'] else 0,
    }
    top_spammers.append(row)

  with open(filename, 'w', encoding='utf-8') as fp:
    json.dump(top_spammers, fp, ensure_ascii=False)
    logger.info(f'wrote to {filename}')

  logger.info("bye bye")


if __name__ == "__main__":
  load_dotenv()
  print(settings)

  parser = argparse.ArgumentParser(description='Fetch top spammers, and save it locally')
  parser.add_argument('-f', '--filename')

  args = parser.parse_args()

  logger.info('hello hello')
  asyncio.run(main(args.filename))
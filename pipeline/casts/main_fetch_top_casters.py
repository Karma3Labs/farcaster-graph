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

def insert_dune_table(api_key, namespace, table_name, scores_df):
  headers = {
      "X-DUNE-API-KEY": api_key,
      "Content-Type": "text/csv"
  }

  url = f"https://api.dune.com/api/v1/table/{namespace}/{table_name}/clear"
  clear_resp = requests.request("POST", url, data="", headers=headers)
  print('clear_resp', clear_resp.status_code, clear_resp.text)

  csv_buffer = StringIO()
  scores_df.to_csv(csv_buffer, index=False)
  csv_buffer.seek(0)

  url = f'https://api.dune.com/api/v1/table/{namespace}/{table_name}/insert'

  insert_resp = requests.request("POST", url, data=csv_buffer.getvalue(), headers=headers)
  print('insert to dune resp', insert_resp.status_code, insert_resp.text)
  return insert_resp



async def main(filename: str):
  pg_dsn = settings.POSTGRES_ASYNC_URI.get_secret_value()
  casters = await cast_db_utils.fetch_top_casters(logger,
                                        pg_dsn)
  top_casters = []
  for caster in casters:
    top_casters.append({ 'i': caster['i'], 'v': caster['v']})

  df = pd.DataFrame(data=top_casters)
  insert_dune_table(settings.DUNE_API_KEY, 'openrank', 'top_caster', df)

  with open(filename, 'w') as fp:
    json.dump(top_casters, fp)
    logger.info(f'wrote to {filename}')

  logger.info("bye bye")

  # end while loop


if __name__ == "__main__":
  load_dotenv()
  print(settings)

  parser = argparse.ArgumentParser(description='Fetch top casters, upload the list to dune, and save it locally')
  parser.add_argument('-f', '--filename')

  args = parser.parse_args()

  logger.info('hello hello')
  asyncio.run(main(args.filename))
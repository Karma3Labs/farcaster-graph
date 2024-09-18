# standard dependencies
import sys
import argparse
from random import sample
import asyncio
from io import StringIO
import json
from datetime import date
from sqlalchemy import create_engine

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


# def insert_dune_table(api_key, namespace, table_name, scores_df):
#   headers = {
#       "X-DUNE-API-KEY": api_key,
#       "Content-Type": "text/csv"
#   }
#
#   url = f"https://api.dune.com/api/v1/table/{namespace}/{table_name}/clear"
#   clear_resp = requests.request("POST", url, data="", headers=headers)
#   print('clear_resp', clear_resp.status_code, clear_resp.text)
#
#   csv_buffer = StringIO()
#   scores_df.to_csv(csv_buffer, index=False)
#   csv_buffer.seek(0)
#
#   url = f'https://api.dune.com/api/v1/table/{namespace}/{table_name}/insert'
#
#   insert_resp = requests.request("POST", url, data=csv_buffer.getvalue(), headers=headers)
#   print('insert to dune resp', insert_resp.status_code, insert_resp.text)
#   return insert_resp


async def main():
    pg_dsn = settings.POSTGRES_ASYNC_URI.get_secret_value()
    casters = await cast_db_utils.fetch_top_casters(logger,
                                                    pg_dsn)
    top_casters = []
    for caster in casters:
        top_casters.append({'i': caster['i'], 'v': caster['v']})

    df = pd.DataFrame(data=top_casters)
    df["date_iso"] = date.today()

    logger.info(df.head())
    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" \
                    % (settings.DB_USER, settings.DB_PASSWORD.get_secret_value(),
                       settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)

    postgres_engine = create_engine(engine_string, connect_args={"connect_timeout": 1000})
    logger.info(postgres_engine)
    with postgres_engine.connect() as connection:
        df.to_sql('top_casters', con=connection, if_exists='append', index=False)


    # insert_dune_table(settings.DUNE_API_KEY, 'openrank', 'top_caster', df)

    # with open(filename, 'w') as fp:
    #   json.dump(top_casters, fp)
    #   logger.info(f'wrote to {filename}')

    logger.info('top casters data updated to DB')

    # end while loop


if __name__ == "__main__":
    load_dotenv()
    print(settings)

    # parser = argparse.ArgumentParser(description='Fetch top casters, persist the dataframe to db')
    #
    # parser.add_argument('-u', '--user')
    # parser.add_argument('-p', '--password')
    # parser.add_argument('-e', '--endpoint')
    #
    # args = parser.parse_args()

    logger.info('hello hello')
    asyncio.run(main())

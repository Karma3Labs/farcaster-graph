# standard dependencies
import logging

# local dependencies
import utils
from config import settings
from . import compute
from .queries import IJVSql

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd

if __name__ == '__main__':
  load_dotenv()
  print(settings)

  logger = logging.getLogger()
  utils.setup_filelogger(logger, __file__)
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()

  df = compute._fetch_interactions_df(logger, pg_dsn)
  logger.info(utils.df_info_to_string(df, with_sample=True))

  pkl_file = '/tmp/fc_interactions_df.pkl'
  logger.info(f"Pickling interactions dataframe to {pkl_file}")
  df.to_pickle(pkl_file)
  logger.info(f"Done pickling interactions dataframe  to {pkl_file}")

  num_ij_pairs = df[df['follows_v'].notna()].groupby(['i', 'j']).ngroups
  logger.info(f"Unique i,j follow pairs: {num_ij_pairs}")

  num_selfies = len(df[df['i']==df['j']])
  logger.info(f"Number of self followers: {num_selfies}")
  
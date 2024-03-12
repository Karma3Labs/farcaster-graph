# standard dependencies
import logging

# local dependencies
import utils
from config import settings
from . import db_utils
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

  pg_dsn = settings.POSTGRES_DSN.get_secret_value()

  df = db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.FOLLOWS)
  logger.info(utils.df_info_to_string(df, with_sample=True))

  num_ij_pairs = df.groupby(['i', 'j']).ngroups
  logger.info(f"Unique i,j pairs: {num_ij_pairs}")

  num_selfies = len(df[df['i']==df['j']])
  logger.info(f"Number of self followers: {num_selfies}")
  
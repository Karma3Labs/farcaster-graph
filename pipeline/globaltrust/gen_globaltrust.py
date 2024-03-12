# standard dependencies
import logging

# local dependencies
import utils
from config import settings
from . import compute
from timer import Timer

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd

def main(pg_dsn: str):
  utils.log_memusage(logger)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.FOLLOWS)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.ENGAGEMENT)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.ACTIVITY)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.OG_CIRCLES)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.OG_ENGAGEMENT)
  compute.run_strategy(logger, pg_dsn, compute.Strategy.OG_ACTIVITY)

if __name__ == '__main__':
  load_dotenv()
  print(settings)

  logger = logging.getLogger()
  utils.setup_filelogger(logger, __file__)
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  # perf optimization to avoid copies unless there is a write on shared data
  pd.set_option("mode.copy_on_write", True)

  main(settings.POSTGRES_DSN.get_secret_value())


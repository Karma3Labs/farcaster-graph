# standard dependencies
import logging

# local dependencies
import utils
from config import settings
from . import compute
from timer import Timer
from . import db_utils

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd

def run_strategy(pg_dsn: str, pg_url: str, strategy: compute.Strategy):
  with Timer(name=f"run_strategy_{strategy}"):
    logger.info(f"Run strategy {strategy}:{strategy.value[0]}:{strategy.value[1]}")

    (lt_df, gt_df) = compute.lt_gt_for_strategy(logger, pg_dsn, strategy)

    with Timer(name=f"insert_localtrust_{strategy}"):
      db_utils.df_insert_copy(logger=logger,
                                pg_url=pg_url,
                                df=lt_df,
                                dest_tablename=settings.DB_TEMP_LOCALTRUST)
    with Timer(name=f"update_localtrust_{strategy}"):
      db_utils.update_date_strategyid(logger=logger,
                                      pg_dsn=pg_dsn,
                                      temp_tbl=settings.DB_TEMP_LOCALTRUST,
                                      strategy_id=strategy.value[1])

    with Timer(name=f"insert_globaltrust_{strategy}"):
      db_utils.df_insert_copy(logger=logger,
                              pg_url=pg_url,
                              df=gt_df,
                              dest_tablename=settings.DB_TEMP_GLOBALTRUST)
    with Timer(name=f"update_globaltrust_{strategy}"):
      db_utils.update_date_strategyid(logger=logger,
                                      pg_dsn=pg_dsn,
                                      temp_tbl=settings.DB_TEMP_GLOBALTRUST,
                                      strategy_id=strategy.value[1])


@Timer(name="main")
def main(pg_dsn: str, pg_url: str):
  utils.log_memusage(logger)
  db_utils.create_temp_table(logger=logger,
                            pg_dsn=pg_dsn,
                            temp_tbl=settings.DB_TEMP_LOCALTRUST,
                            orig_tbl=settings.DB_LOCALTRUST)
  db_utils.create_temp_table(logger=logger,
                              pg_dsn=pg_dsn,
                              temp_tbl=settings.DB_TEMP_GLOBALTRUST,
                              orig_tbl=settings.DB_GLOBALTRUST)
  run_strategy(pg_dsn, pg_url, compute.Strategy.FOLLOWS)
  run_strategy(pg_dsn, pg_url, compute.Strategy.ENGAGEMENT)
  # run_strategy(pg_dsn, pg_url, compute.Strategy.ACTIVITY)


if __name__ == '__main__':
  load_dotenv()
  print(settings)

  logger = logging.getLogger()
  utils.setup_filelogger(logger, __file__)
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  # perf optimization to avoid copies unless there is a write on shared data
  pd.set_option("mode.copy_on_write", True)

  main(settings.POSTGRES_DSN.get_secret_value(),
       settings.POSTGRES_URL.get_secret_value())


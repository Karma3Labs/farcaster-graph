# standard dependencies
import sys

# local dependencies
import utils, db_utils
from config import settings
from . import compute
from timer import Timer

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd
from loguru import logger
import gc

logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "channels.channel_utils": "TRACE",
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)

def run_strategy(pg_dsn: str, pg_url: str, strategy: compute.Strategy):
  with Timer(name=f"run_strategy_{strategy}"):
    logger.info(f"Run strategy {strategy}:{strategy.value[0]}:{strategy.value[1]}")

    (lt_df, gt_df) = compute.lt_gt_for_strategy(logger, pg_dsn, strategy)

    with Timer(name=f"insert_localtrust_{strategy}"):
      db_utils.df_insert_copy(pg_url=pg_url,
                                df=lt_df,
                                dest_tablename=settings.DB_TEMP_LOCALTRUST)
    with Timer(name=f"update_localtrust_{strategy}"):
      db_utils.update_date_strategyid(pg_dsn=pg_dsn,
                                      temp_tbl=settings.DB_TEMP_LOCALTRUST,
                                      strategy_id=strategy.value[1])

    # manually call garbage collector to free up localtrust sql immediately
    utils.log_memusage(logger)
    logger.info(f"calling garbage collector to free up localtrust sql immediately")
    gc.collect()
    utils.log_memusage(logger)

    with Timer(name=f"insert_globaltrust_{strategy}"):
      db_utils.df_insert_copy(pg_url=pg_url,
                              df=gt_df,
                              dest_tablename=settings.DB_TEMP_GLOBALTRUST)
    with Timer(name=f"update_globaltrust_{strategy}"):
      db_utils.update_date_strategyid(pg_dsn=pg_dsn,
                                      temp_tbl=settings.DB_TEMP_GLOBALTRUST,
                                      strategy_id=strategy.value[1])
    # manually call garbage collector to free up globaltrust sql immediately
    utils.log_memusage(logger)
    logger.info(f"calling garbage collector to free up globaltrust sql immediately")
    gc.collect()
    utils.log_memusage(logger)



@Timer(name="main")
def main(pg_dsn: str, pg_url: str):
  utils.log_memusage(logger)
  db_utils.create_temp_table(pg_dsn=pg_dsn,
                            temp_tbl=settings.DB_TEMP_LOCALTRUST,
                            orig_tbl=settings.DB_LOCALTRUST)
  db_utils.create_temp_table(pg_dsn=pg_dsn,
                              temp_tbl=settings.DB_TEMP_GLOBALTRUST,
                              orig_tbl=settings.DB_GLOBALTRUST)
  run_strategy(pg_dsn, pg_url, compute.Strategy.FOLLOWS)
  run_strategy(pg_dsn, pg_url, compute.Strategy.ENGAGEMENT)
  # run_strategy(pg_dsn, pg_url, compute.Strategy.ACTIVITY)


if __name__ == '__main__':
  load_dotenv()
  print(settings)

  # perf optimization to avoid copies unless there is a write on shared data
  pd.set_option("mode.copy_on_write", True)

  main(settings.POSTGRES_DSN.get_secret_value(),
       settings.POSTGRES_URL.get_secret_value())


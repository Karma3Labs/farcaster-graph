# standard dependencies
import sys
import argparse
from datetime import datetime

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

def get_temp_tbl_names(target_date: str):
  date_suffix = "" if target_date is None else f"_{datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y%m%d')}"
  tmp_lt_name = f"{settings.DB_TEMP_LOCALTRUST}{date_suffix}"
  tmp_gt_name = f"{settings.DB_TEMP_GLOBALTRUST}{date_suffix}"
  return (tmp_lt_name, tmp_gt_name)

def run_strategy(pg_dsn: str, pg_url: str, strategy: compute.Strategy, target_date: str = None):
  with Timer(name=f"run_strategy_{strategy}"):
    logDate = "today" if target_date is None else f"{target_date}"      
    logger.info(f"Run strategy {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate}")

    (lt_df, gt_df) = compute.lt_gt_for_strategy(logger, pg_dsn, strategy, target_date)

    if target_date:
      logger.info(f"Target computation to calculate global/localtrust for {logDate}")
      (tmp_lt_name, tmp_gt_name) = get_temp_tbl_names(target_date)

      ####
      # We don't need to backfill the localtrust table since we only keep the latest day's copy
      # Code is available here in case we want to turn this on
      ####
      # with Timer(name=f"insert_localtrust_{strategy}"):
      #   db_utils.df_insert_copy(pg_url=pg_url,
      #                           df=lt_df,
      #                           dest_tablename=tmp_lt_name)
      # with Timer(name=f"update_localtrust_{strategy}"):
      #   db_utils.update_date_strategyid(pg_dsn=pg_dsn,
      #                                   temp_tbl=tmp_lt_name,
      #                                   strategy_id=strategy.value[1],
      #                                   date_str = target_date)

      with Timer(name=f"insert_globaltrust_{strategy}"):
        db_utils.df_insert_copy(pg_url=pg_url,
                                df=gt_df,
                                dest_tablename=tmp_gt_name)
      with Timer(name=f"update_globaltrust_{strategy}"):
        db_utils.update_date_strategyid(pg_dsn=pg_dsn,
                                        temp_tbl=tmp_gt_name,
                                        strategy_id=strategy.value[1],
                                        date_str=target_date)
      # manually call garbage collector to free up globaltrust sql immediately
      utils.log_memusage(logger)
      logger.info(f"calling garbage collector to free up globaltrust sql immediately")
      gc.collect()
      utils.log_memusage(logger)

    else:

      logger.info(f"Target computation to calculate global/localtrust for today")
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
def main(pg_dsn: str, pg_url: str, target_date: str = None):
  utils.log_memusage(logger)
  (tmp_lt_name, tmp_gt_name) = get_temp_tbl_names(target_date)
  db_utils.create_temp_table(pg_dsn=pg_dsn,
                              temp_tbl=tmp_lt_name,
                              orig_tbl=settings.DB_LOCALTRUST)
  db_utils.create_temp_table(pg_dsn=pg_dsn,
                              temp_tbl=tmp_gt_name,
                              orig_tbl=settings.DB_GLOBALTRUST)
  run_strategy(pg_dsn, pg_url, compute.Strategy.FOLLOWS, target_date)
  run_strategy(pg_dsn, pg_url, compute.Strategy.ENGAGEMENT, target_date)
  # run_strategy(pg_dsn, pg_url, compute.Strategy.ACTIVITY, target_date)

if __name__ == '__main__':
  load_dotenv()
  print(settings)

  # perf optimization to avoid copies unless there is a write on shared data
  pd.set_option("mode.copy_on_write", True)

  parser = argparse.ArgumentParser(description='Run global trust computation with optional date condition.')
  parser.add_argument('--date', type=str, help='Date condition for the queries, format: YYYY-MM-DD')
  args = parser.parse_args()

  if args.date:
    try:
      target_date = f"{args.date}"
      # Ensure the date is valid
      datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
      logger.error("Invalid date format. Please use YYYY-MM-DD.")
      sys.exit(1)
  else:
    target_date = None

  main(settings.POSTGRES_DSN.get_secret_value(),
       settings.POSTGRES_URL.get_secret_value(),
       target_date)

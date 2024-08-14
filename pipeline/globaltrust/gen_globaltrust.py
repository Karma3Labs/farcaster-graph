# standard dependencies
import sys
import argparse
from datetime import datetime
from pathlib import Path
import os

# local dependencies
import utils
from config import settings
from . import compute
from timer import Timer

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd
from loguru import logger

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

def gen_lt_gt_filepath(basedir:Path, strategy: compute.Strategy, target_date: str) -> tuple[Path, Path]:
  lt_filename = f"localtrust_{strategy}_{target_date}.csv"
  gt_filename = f"globaltrust_{strategy}_{target_date}.csv"
  return (os.path.join(basedir, lt_filename), os.path.join(basedir, gt_filename))


def run_strategy(pg_dsn: str, pg_url: str, outdir:Path, strategy: compute.Strategy, target_date: str = None):
  with Timer(name=f"run_strategy_{strategy}"):
    logDate = "today" if target_date is None else f"{target_date}"      
    logger.info(f"Run strategy {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate}")

    (lt_df, gt_df) = compute.lt_gt_for_strategy(logger, pg_dsn, strategy, target_date)

    (lt_filename, gt_filename) = gen_lt_gt_filepath(target_date)
    logger.info(f"CSV filenames: {(lt_filename, gt_filename)}")

    with Timer(name=f"localtrust_{strategy}_to_csv"):
      lt_df.to_csv(lt_filename, index=False, header=True)
    with Timer(name=f"globaltrust_{strategy}_to_csv"):
      gt_df.to_csv(gt_filename, index=False, header=True)

@Timer(name="main")
def main(pg_dsn: str, pg_url: str, outdir:Path, target_date: str = None):
  utils.log_memusage(logger)
  run_strategy(pg_dsn, pg_url, outdir, compute.Strategy.FOLLOWS, target_date)
  run_strategy(pg_dsn, pg_url, outdir, compute.Strategy.ENGAGEMENT, target_date)
  # run_strategy(pg_dsn, pg_url, outdir, compute.Strategy.ACTIVITY, target_date)

if __name__ == '__main__':
    load_dotenv()
    print(settings)

    # perf optimization to avoid copies unless there is a write on shared data
    pd.set_option("mode.copy_on_write", True)

    parser = argparse.ArgumentParser(
        description="Run global trust computation with optional date condition."
    )
    parser.add_argument(
        "-o",
        "--outdir",
        help="output directory",
        required=True,
        type=lambda f: Path(f).expanduser().resolve(),
    )
    parser.add_argument(
        "-d",
        "--date",
        help="Date condition for the queries, format: YYYY-MM-DD",
        required=False,
        type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
    )
    args = parser.parse_args()
    print(args)

    target_date:str = None
    if hasattr(args, 'date'):
      target_date = args.date.strftime("%Y-%m-%d")

    main(
        settings.POSTGRES_DSN.get_secret_value(),
        settings.POSTGRES_URL.get_secret_value(),
        args.outdir,
        target_date,
    )

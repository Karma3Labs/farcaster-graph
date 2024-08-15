# standard dependencies
import sys
import argparse
from datetime import datetime
from pathlib import Path
import os
import csv

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

def gen_lt_gt_filepath(
    basedir: Path, strategy: compute.Strategy, target_date: str
) -> tuple[Path, Path]:
    lt_filename = f"localtrust.{strategy.name.lower()}{'_'+target_date if target_date else '' }.csv"
    gt_filename = f"globaltrust.{strategy.name.lower()}{'_'+target_date if target_date else '' }.csv"
    lt_stats_filename = f"localtrust_stats.{strategy.name.lower()}{'_'+target_date if target_date else '' }.csv"
    return (
        os.path.join(basedir, lt_filename),
        os.path.join(basedir, gt_filename),
        os.path.join(basedir, lt_stats_filename),
    )

def gen_strategy_to_csv(
    pg_dsn: str,
    outdir: Path,
    strategy: compute.Strategy,
    target_date: str = None,
) :
    with Timer(name=f"run_strategy_{strategy}"):
        logDate = "today" if target_date is None else f"{target_date}"
        logger.info(
            f"Run strategy {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate}"
        )

        (lt_df, gt_df) = compute.lt_gt_for_strategy(
            logger, pg_dsn, strategy, target_date
        )

        (lt_filename, gt_filename, lt_stats_filename) = gen_lt_gt_filepath(outdir, strategy, target_date)
        logger.info(f"CSV filenames: {(lt_filename, gt_filename, lt_stats_filename)}")

        strategy_id: int = strategy.value[1]
        dt_str: str = (
            target_date
            if target_date
            else datetime.strftime(datetime.now(), "%Y-%m-%d")
        )

        with Timer(name=f"localtrust_{strategy}_to_csv"):
            lt_df["date"] = dt_str
            lt_df["strategy_id"] = strategy_id
            lt_df.to_csv(lt_filename, index=False, header=True)

        with Timer(name=f"globaltrust_{strategy}_to_csv"):
            gt_df["date"] = dt_str
            gt_df["strategy_id"] = strategy_id
            gt_df.to_csv(gt_filename, index=False, header=True)
        lt_stats = lt_df["v"].describe()
        with Timer(name=f"localtrust_stats_{strategy}_to_csv"):
          stats_row = (
              dt_str,
              int(lt_stats["count"]),
              lt_stats["mean"],
              lt_stats["std"],
              lt_stats["max"] - lt_stats["min"],
          )
          stats_header = [
              "date",
              f"strategy_id_{strategy_id}_row_count",
              f"strategy_id_{strategy_id}_mean",
              f"strategy_id_{strategy_id}_stddev",
              f"strategy_id_{strategy_id}_range",
          ]
          with open(lt_stats_filename, 'w', newline='') as stats_file:
            writer = csv.writer(stats_file)
            writer.writerow(stats_header)
            writer.writerow(stats_row)

@Timer(name="main")
def main(pg_dsn: str, outdir:Path, target_date: str = None):
  utils.log_memusage(logger)
  gen_strategy_to_csv(pg_dsn, outdir, compute.Strategy.FOLLOWING, target_date)
  gen_strategy_to_csv(pg_dsn, outdir, compute.Strategy.ENGAGEMENT, target_date)
  # gen_strategy_to_csv(pg_dsn, outdir, compute.Strategy.ACTIVITY, target_date)



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
    if args.date:
      target_date = args.date.strftime("%Y-%m-%d")

    main(
        settings.POSTGRES_DSN.get_secret_value(),
        args.outdir,
        target_date,
    )

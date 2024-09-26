# standard dependencies
import sys
import argparse
from datetime import datetime
from pathlib import Path
import os
import csv
from enum import Enum

# local dependencies
import utils
from config import settings
from . import compute
from timer import Timer

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd
from loguru import logger

class Step(Enum):
  prep = 1
  compute_following = 2
  compute_engagement = 3
  graph = 4
  compute_v3engagement = 9

  def __str__(self):
    return self.name

  @staticmethod
  def from_string(s):
    try:
        return Step[s]
    except KeyError:
        raise ValueError()

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

def gen_filepaths(
    basedir: Path, strategy: compute.Strategy, target_date: str,
) -> tuple[Path, Path, Path, Path]:
    
    suffix =  f"_{target_date}" if target_date else ""

    lt_filename = f"localtrust.{strategy.name.lower()}{suffix}.csv"
    gt_filename = f"globaltrust.{strategy.name.lower()}{suffix}.csv"
    lt_stats_filename = f"localtrust_stats.{strategy.name.lower()}{suffix}.csv"
    pt_stats_filename = f"pretrust.{strategy.name.lower()}{suffix}.csv"
    return (
        os.path.join(basedir, lt_filename),
        os.path.join(basedir, gt_filename),
        os.path.join(basedir, lt_stats_filename),
        os.path.join(basedir, pt_stats_filename),
    )

def gen_localtrust_to_csv(
    pg_dsn: str,
    outdir: Path,
    strategy: compute.Strategy,
    target_date: str = None,
    interval: int = 0,
) :
    with Timer(name=f"gen_localtrust_{strategy}"):
        logDate = "today" if target_date is None else f"{target_date}"
        logger.info(
            f"Generate localtrust {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate} with interval {interval}"
        )

        lt_df = compute.localtrust_for_strategy(logger, pg_dsn, strategy, target_date, interval)

        (lt_filepath, _, lt_stats_filepath, _) = gen_filepaths(outdir, strategy, target_date)
        logger.info(f"CSV filepaths: {lt_filepath, lt_stats_filepath}")

        strategy_id: int = strategy.value[1]
        dt_str: str = (
            target_date
            if target_date
            else datetime.strftime(datetime.now(), "%Y-%m-%d")
        )
        with Timer(name=f"localtrust_{strategy}_to_csv"):
            lt_df["date"] = dt_str
            lt_df["strategy_id"] = strategy_id
            lt_df['v'] = lt_df['v'].astype('int32')
            lt_df.to_csv(lt_filepath, index=False, header=True)

        lt_stats = lt_df["v"].describe()
        with Timer(name=f"localtrust_stats_{strategy}_to_csv"):
          stats_row = (
              dt_str,
              int(lt_stats["count"]),
              lt_stats["mean"],
              lt_stats["std"],
              lt_stats["max"] - lt_stats["min"],
              strategy_id,
          )
          stats_header = [
              "date",
              f"strategy_id_row_count",
              f"strategy_id_mean",
              f"strategy_id_stddev",
              f"strategy_id_range",
              f"strategy_id",
          ]
          with open(lt_stats_filepath, 'w', newline='') as stats_file:
            writer = csv.writer(stats_file)
            writer.writerow(stats_header)
            writer.writerow(stats_row)

def gen_pretrust_to_csv(
    pg_dsn: str,
    outdir: Path,
    strategy: compute.Strategy,
    target_date: str = None,
) :
    with Timer(name=f"gen_pretrust_{strategy}"):
        logDate = "today" if target_date is None else f"{target_date}"
        logger.info(
            f"Generate pretrust {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate}"
        )

        pt_df = compute.pretrust_for_strategy(logger, pg_dsn, strategy)

        (_, _, _, pt_filepath) = gen_filepaths(outdir, strategy, target_date)
        logger.info(f"CSV filepath: {pt_filepath}")

        with Timer(name=f"pretrust_{strategy}_to_csv"):
            pt_df.to_csv(pt_filepath, index=False, header=True)

def gen_globaltrust_to_csv(
    ptcsv: Path,
    ltcsv: Path, 
    outdir: Path,
    strategy: compute.Strategy,
    target_date: str = None,
) :
    with Timer(name=f"gen_globaltrust_{strategy}"):
        logDate = "today" if target_date is None else f"{target_date}"
        logger.info(
            f"Generate globaltrust {strategy}:{strategy.value[0]}:{strategy.value[1]} for {logDate}"
        )

        (_, gt_filepath, _, _) = gen_filepaths(outdir, strategy, target_date)
        logger.info(f"CSV filepaths: {(gt_filepath)}")
        gt_df = compute.globaltrust_for_strategy(logger, ptcsv, ltcsv, strategy)

        strategy_id: int = strategy.value[1]
        dt_str: str = (
            target_date
            if target_date
            else datetime.strftime(datetime.now(), "%Y-%m-%d")
        )
        with Timer(name=f"globaltrust_{strategy}_to_csv"):
            gt_df["date"] = dt_str
            gt_df["strategy_id"] = strategy_id
            gt_df.to_csv(gt_filepath, index=False, header=True)

@Timer(name="main")
def main(step:Step, pg_dsn: str, ptcsv:Path, ltcsv:Path, outdir:Path, target_date: str = None):
  utils.log_memusage(logger)
  match step:
    case Step.graph:
        gen_localtrust_to_csv(pg_dsn, outdir, compute.Strategy.GRAPH_90DV3, target_date = None, interval = 90)
    case Step.prep:
      gen_localtrust_to_csv(pg_dsn, outdir, compute.Strategy.FOLLOWING, target_date)
      gen_localtrust_to_csv(pg_dsn, outdir, compute.Strategy.ENGAGEMENT, target_date)
      gen_localtrust_to_csv(pg_dsn, outdir, compute.Strategy.V3ENGAGEMENT, target_date)
      gen_pretrust_to_csv(pg_dsn, outdir, compute.Strategy.FOLLOWING, target_date)
      gen_pretrust_to_csv(pg_dsn, outdir, compute.Strategy.ENGAGEMENT, target_date)
      gen_pretrust_to_csv(pg_dsn, outdir, compute.Strategy.V3ENGAGEMENT, target_date)
    case Step.compute_following:
      gen_globaltrust_to_csv(ptcsv, ltcsv, outdir, compute.Strategy.FOLLOWING, target_date) 
    case Step.compute_engagement:
      gen_globaltrust_to_csv(ptcsv, ltcsv, outdir, compute.Strategy.ENGAGEMENT, target_date)
    case Step.compute_engagement_v3:
      gen_globaltrust_to_csv(ptcsv, ltcsv, outdir, compute.Strategy.V3ENGAGEMENT, target_date)

if __name__ == '__main__':
    load_dotenv()
    print(settings)

    # perf optimization to avoid copies unless there is a write on shared data
    pd.set_option("mode.copy_on_write", True)

    parser = argparse.ArgumentParser(
        description="Run global trust computation with optional date condition."
    )
    parser.add_argument(
        "-s",
        "--step",
        help="prep or compute",
        required=True,
        choices=list(Step),
        type=Step.from_string,
    )
    parser.add_argument(
        "-l",
        "--ltcsv",
        help="localtrust csv in i,j,v format required for compute",
        required=False,
        type=lambda f: Path(f).expanduser().resolve(),
    )
    parser.add_argument(
        "-p",
        "--ptcsv",
        help="pretrust csv in i,v format required for compute",
        required=False,
        type=lambda f: Path(f).expanduser().resolve(),
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

    if args.step in [Step.compute_following, Step.compute_engagement] and (
        not args.ltcsv or not args.ptcsv
    ):
        raise ValueError("Step Compute requires localtrust and preturst argument")

    target_date:str = None
    if args.date:
      target_date = args.date.strftime("%Y-%m-%d")

    main(
        args.step,
        settings.POSTGRES_DSN.get_secret_value(),
        args.ptcsv,
        args.ltcsv,
        args.outdir,
        target_date,
    )

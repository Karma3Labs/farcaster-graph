# standard dependencies
import sys
import argparse
import random
from enum import Enum
from pathlib import Path
import time

# local dependencies
import utils
import db_utils
import go_eigentrust
from config import settings
from . import channel_utils
from . import channel_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas as pd

# Performance optimization to avoid copies unless there is a write on shared data
pd.set_option("mode.copy_on_write", True)

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "db_utils": "DEBUG",
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)

load_dotenv()

def prep_channels(run_id: str, num_days: int, num_batches: int):
    logger.info(
        f"Prep channels for run ID: {run_id} num_days: {num_days} num_batches: {num_batches}"
    )
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = 120_000
    try:
        num_channels = channel_db_utils.prep_channel_rank_log(
            logger=logger, 
            pg_dsn=pg_dsn, 
            timeout_ms=sql_timeout_ms, 
            run_id=run_id, 
            num_days=num_days, 
            num_batches=num_batches
        )
        logger.info(f"{num_channels} prepped for ranking")
    except Exception as e:
        logger.error(f"Failed to prep channel rank: {e}")
        raise e
    

def process_channels(
    run_id: str,
    num_days: int,
    batch_id: int,
    channel_seeds_csv: Path,
    channel_bots_csv: Path,
):
    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_bots_df = channel_utils.read_channel_bot_fids_csv(channel_bots_csv)
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = 120_000
    try:
        channel_ids = channel_db_utils.update_channel_rank_batch_inprogress(
            logger=logger, 
            pg_dsn=pg_dsn, 
            timeout_ms=sql_timeout_ms, 
            run_id=run_id, 
            num_days=num_days, 
            batch_id=batch_id
        )
        logger.info(f"{len(channel_ids)} marked inprogress for ranking")
        logger.info(f"{channel_ids} marked inprogress for ranking")
    except Exception as e:
        logger.error(f"Failed to mark channel rank inprogress: {e}")
        raise e

    pg_url = settings.ALT_POSTGRES_URL.get_secret_value()
    for cid in channel_ids:
        try:
            start_time = time.perf_counter()
            channel_lt_df, pretrust_fids, absent_fids = channel_utils.prep_trust_data(
                cid, channel_seeds_df, channel_bots_df, pg_dsn, pg_url, num_days
            )
            if len(channel_lt_df) > 0:
                scores_df = channel_utils.compute_goeigentrust(
                    cid=cid,
                    channel_lt_df=channel_lt_df,
                    pretrust_fids=pretrust_fids,
                    interval=num_days,
                )
                num_fids = len(scores_df)
                inactive_seeds = absent_fids
                if scores_df is not None:
                    channel_db_utils.insert_channel_scores_df(
                        logger=logger, cid=cid, scores_df=scores_df, pg_url=pg_url
                    )
            else:
                logger.warning(f"No local trust for channel {cid} in last {num_days} days")
                num_fids = 0
                inactive_seeds = pretrust_fids
            num_fids = None
            inactive_seeds = None

            elapsed_time_ms = int((time.perf_counter() - start_time) * 1_000)
            channel_db_utils.update_channel_rank_for_cid(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
                run_id=run_id,
                num_days=num_days,
                batch_id=batch_id,
                channel_id=cid,
                num_fids=num_fids,
                inactive_seeds=inactive_seeds,
                elapsed_time_ms=elapsed_time_ms,
                is_error=False
            )
        except Exception as e:
            logger.error(f"Failed to process channel {cid}: {e}")
            raise e

if __name__ == "__main__":
    logger.debug('hello main')

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--task",
        type=str,
        help="task to perform: prep or process",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--run_id",
        type=str,
        help="airflow run ID for processing",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--num_days",
        type=int,
        help="number of days to consider for processing, 0 means lifetime",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--num_batches",
        type=int,
        help="number of Airflow tasks aka batches aka chunks",
        required=False
    )
    parser.add_argument(
        "-s",
        "--seeds",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=False,
    )
    parser.add_argument(
        "-b",
        "--bots",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=False,
    )
    parser.add_argument(
        "-i",
        "--batch_id",
        type=str,
        help="batch ID for processing, only used for process task",
        required=False,
    )

    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.task == 'prep':
        if not args.num_batches:
            logger.error("Number of batches is required for prep task.")
            sys.exit(1)
        prep_channels(
            run_id=args.run_id,
            num_days=args.num_days,
            num_batches= args.num_batches
        )
    elif args.task == 'process':
        if not args.seeds or not args.bots or not args.batch_id:
                logger.error("Channel Seed Peers CSV, Bot FIDs CSV and Batch ID are required for processing.")
                sys.exit(1)
        process_channels(
            run_id=args.run_id,
            num_days=args.num_days,
            batch_id=args.batch_id,
            channel_seeds_csv=args.seeds,
            channel_bots_csv=args.bots,
        )
    else:
        logger.error("Invalid task specified. Use 'fetch' or 'process'.")
        sys.exit(1)



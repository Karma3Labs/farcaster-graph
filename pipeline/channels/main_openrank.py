# standard dependencies
import argparse
import csv
import json
import os
import random
import sys
from enum import Enum
from pathlib import Path
from typing import Tuple

import pandas as pd
import tomlkit as toml

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

import db_utils

# local dependencies
import utils
from config import OpenRankSettings, settings

from . import channel_utils, openrank_utils

openrank_settings = OpenRankSettings()

# Performance optimization to avoid copies unless there is a write on shared data
pd.set_option("mode.copy_on_write", True)

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "db_utils": "DEBUG",
    "silentlib": False,
}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)

load_dotenv()


class Category(Enum):
    test = "test"
    prod = "prod"


def fetch_results(
    out_dir: Path,
    category: str,
):
    pg_url = settings.ALT_POSTGRES_URL.get_secret_value()
    file = os.path.join(out_dir, openrank_settings.REQ_IDS_FILENAME)
    if not os.path.exists(file):
        raise Exception(f"Missing file {file}")

    openrank_manager_address = openrank_settings.MANAGER_ADDRESS;

    req_ids_df = pd.read_csv(file, header=None, names=["channel_ids", "req_id"])
    # duplicates possible if process_category task was retried multiple times by Airflow dag
    req_ids_df = req_ids_df.drop_duplicates(subset=["req_id"], keep="last")
    row = req_ids_df.iloc[-1]

    req_id = row["req_id"]

    out_folder = os.path.join(out_dir, "./scores/")
    if os.path.exists(out_folder):
        logger.warning(f"Output folder {out_folder} already exists. Overwriting")

    try:
        openrank_utils.compute_watch(openrank_settings, req_id, out_dir)
        openrank_utils.download_results(openrank_settings, req_id, out_folder)

        with open(os.path.join(out_dir, "metadata.json"), "r") as file:
            data = json.load(file)

        metadata_df = pd.DataFrame(
            columns=[
                "category",
                "openrank_manager_address",
                "req_id",
                "request_tx_hash",
                "results_tx_hash",
                "challenge_tx_hash",
            ],
            data=[
                [
                    category,
                    openrank_manager_address,
                    req_id,
                    data["request_tx_hash"],
                    data["results_tx_hash"],
                    data["challenge_tx_hash"],
                ]
            ],
        )
        print(metadata_df)

        db_utils.df_insert_copy(
            pg_url=pg_url, df=metadata_df, dest_tablename="openrank_channel_metadata"
        )
    except Exception as e:
        logger.error(f"Failed to download results, req_id {req_id}: {e}")

    return


def process_category(
    category: str,
    out_dir: Path,
):
    pg_url = settings.ALT_POSTGRES_URL.get_secret_value()
    channels_df = channel_utils.fetch_channels_for_category_df(pg_url, category)
    try:
        lt_folder = os.path.join(out_dir, "./trust/")
        pt_folder = os.path.join(out_dir, "./seed/")

        if not os.path.exists(lt_folder) or not os.path.exists(pt_folder):
            raise Exception(f"Missing folders ./trust or ./seed")

        req_id = openrank_utils.update_and_compute(
            openrank_settings,
            lt_folder=lt_folder,
            pt_folder=pt_folder,
        )

        with (
            open(
                file=os.path.join(out_dir, openrank_settings.REQ_IDS_FILENAME),
                mode="a",  # Note - multiple processes within an airflow dag will write to the same file
                buffering=os.O_NONBLOCK,  # Note - this setting is redundant on most OS
                newline="",
            ) as f
        ):
            write = csv.writer(f)
            write.writerow([channels_df["channel_id"].values, req_id])

    except Exception as e:
        logger.error(f"failed to process a channel: {cid}: {e}")
        raise e

    return


def write_openrank_files(
    cid: str,
    interval: int,
    localtrust_df: pd.DataFrame,
    pretrust_df: pd.DataFrame,
    out_dir: Path,
):
    lt_file = "./trust/{cid}.csv".format(cid=cid)
    lt_file = os.path.join(out_dir, lt_file)
    logger.info(f"Saving localtrust for channel {cid} to {lt_file}")
    logger.info(
        f"Localtrust: {utils.df_info_to_string(localtrust_df, with_sample=True)}"
    )
    if len(localtrust_df) == 0:
        localtrust_df = pd.DataFrame(columns=["i", "j", "v"])
    localtrust_df.to_csv(lt_file, index=False)

    pt_file = "./seed/{cid}.csv".format(cid=cid)
    pt_file = os.path.join(out_dir, pt_file)
    logger.info(f"Saving pretrust for channel {cid} to {pt_file}")
    logger.info(f"Pretrust: {utils.df_info_to_string(pretrust_df, with_sample=True)}")
    if len(pretrust_df) == 0:
        pretrust_df = pd.DataFrame(columns=["i", "v"])
    pretrust_df.to_csv(pt_file, index=False)

    return


def gen_category_files(
    channel_seeds_csv: Path,
    channel_bots_csv: Path,
    category: str,
    out_dir: Path,
):
    # DSN used with Pandas to SQL, and URL with direct SQL queries
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    pg_url = settings.ALT_POSTGRES_URL.get_secret_value()

    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_bots_df = channel_utils.read_channel_bot_fids_csv(channel_bots_csv)
    channels_df = channel_utils.fetch_channels_for_category_df(pg_url, category)
    missing_seed_fids = []

    for index, channel in channels_df.iterrows():
        try:
            cid = channel["channel_id"]
            interval = int(channel["interval_days"])

            localtrust_df, pretrust_fid_list, absent_fids = (
                channel_utils.prep_trust_data(
                    cid,
                    channel_seeds_df,
                    channel_bots_df,
                    pg_dsn,
                    pg_url,
                    interval,
                )
            )
            logger.info(
                f"Localtrust: {utils.df_info_to_string(localtrust_df, with_sample=True)}"
            )
            if len(pretrust_fid_list) > 0:
                logger.info(
                    f"Pretrust sample: {random.choices(pretrust_fid_list, k=10)}"
                )
            else:
                logger.warning(f"No pretrust for channel {cid} for interval {interval}")

            # Filter out entries where i == j
            localtrust_df = localtrust_df[localtrust_df["i"] != localtrust_df["j"]]

            if len(localtrust_df) == 0:
                if interval > 0:
                    logger.info(
                        f"No local trust for channel {cid} for interval {interval}"
                    )
                else:
                    logger.error(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )
                    # this is unexpected because if a channel exists there must exist at least one ijv
                    raise Exception(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )
            else:
                pretrust_df = channel_utils.pretrust_list_to_df(pretrust_fid_list)

                # Future Feature: keep track and clean up seed fids that have had no engagement in channel
                missing_seed_fids.append({cid: absent_fids})

                write_openrank_files(
                    cid=cid,
                    interval=interval,
                    localtrust_df=localtrust_df,
                    pretrust_df=pretrust_df,
                    out_dir=out_dir,
                )

        except Exception as e:
            logger.error(f"failed to process a channel: {cid}: {e}")
            raise e

    logger.info(missing_seed_fids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--seed",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the channel id - seed CSV file. For example, -s /path/to/file.csv",
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
        "-t",
        "--task",
        type=str,
        help="task to perform: fetch or process",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--category",
        choices=list(Category),
        type=Category,
        required=True,
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=lambda f: Path(f).expanduser().resolve(),
        help="output directory for process_category task",
        required=False,
    )
    args = parser.parse_args()
    print(args)

    logger.debug("hello main")

    category = args.category.value
    if not hasattr(args, "outdir"):
        logger.error("Output directory is required.")
        sys.exit(1)

    if args.task == "fetch_results":
        fetch_results(out_dir=args.outdir, category=category)
    else:
        if args.task == "gen_category_files":
            if not hasattr(args, "seed"):
                logger.error(
                    "Seed csv file, previous directory and category mapping are required for gen_category_files task."
                )
                sys.exit(1)

            gen_category_files(
                channel_seeds_csv=args.seed,
                channel_bots_csv=args.bots,
                category=category,
                out_dir=args.outdir,
            )
        elif args.task == "process_category":
            process_category(
                category=category,
                out_dir=args.outdir,
            )
        else:
            logger.error(
                "Invalid task specified. Use 'process_category' or 'gen_category_files'."
            )
            sys.exit(1)

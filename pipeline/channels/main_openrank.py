# standard dependencies
import argparse
import csv
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
    domains_category: str,
):
    file = os.path.join(out_dir, openrank_settings.REQ_IDS_FILENAME)
    if not os.path.exists(file):
        raise Exception(f"Missing file {file}")

    req_ids_df = pd.read_csv(
        file, header=None, names=["channel_id", "interval_days", "req_id"]
    )
    # duplicates possible if process_domains task was retried multiple times by Airflow dag
    req_ids_df = req_ids_df.drop_duplicates(subset=["req_id"], keep="last")

    for _, row in req_ids_df.iterrows():
        cid = row["channel_id"]
        interval = row["interval_days"]
        req_id = row["req_id"]

        out_folder = os.path.join(out_dir, "./scores/")
        if os.path.exists(out_folder):
            logger.warning(f"Output folder {out_folder} already exists. Overwriting")

        try:
            openrank_utils.download_results(openrank_settings, req_id, out_folder)
        except Exception as e:
            logger.error(
                f"Failed to download results for channel {cid}, interval {interval}, req_id {req_id}: {e}"
            )
            continue
    return


def process_domains(
    channel_ids_list: list[str],
    domains_category: str,
    out_dir: Path,
):
    pg_url = settings.POSTGRES_URL.get_secret_value()
    channel_domain_df = channel_utils.fetch_channel_domain_df(
        pg_url, domains_category, channel_ids_list
    )
    for cid in channel_ids_list:
        try:
            channel = channel_domain_df[channel_domain_df["channel_id"] == cid]
            interval = channel["interval_days"].values[0]

            lt_folder = os.path.join(out_dir, "./trust/")
            pt_folder = os.path.join(out_dir, "./seed/")

            if not os.path.exists(lt_folder) or not os.path.exists(pt_folder):
                raise Exception(f"Missing folders for {cid}")

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
                write.writerow([cid, interval, req_id])

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


def gen_domain_files(
    channel_seeds_csv: Path,
    channel_bots_csv: Path,
    channel_ids_list: list[str],
    domains_category: str,
    out_dir: Path,
):
    # DSN used with Pandas to SQL, and URL with direct SQL queries
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_bots_df = channel_utils.read_channel_bot_fids_csv(channel_bots_csv)
    channel_domain_df = channel_utils.fetch_channel_domain_df(
        pg_url, domains_category, channel_ids_list
    )
    missing_seed_fids = []

    for cid in channel_ids_list:
        try:
            channel = channel_domain_df[channel_domain_df["channel_id"] == cid]
            interval = int(channel["interval_days"].values[0])

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
                    return {cid: []}
                else:
                    logger.error(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )
                    # this is unexpected because if a channel exists there must exist at least one ijv
                    raise Exception(
                        f"No local trust for channel {cid} for lifetime engagement"
                    )

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
        "-ids",
        "--channel_ids",
        type=str,
        help="channel IDs for processing, only used for process task",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=lambda f: Path(f).expanduser().resolve(),
        help="output directory for process_domain task",
        required=False,
    )
    args = parser.parse_args()
    print(args)

    logger.debug("hello main")

    domains_category = args.category.value
    # TODO replace this nested if-else with argparse groups
    if args.task == "fetch_domains":
        pg_url = settings.POSTGRES_URL.get_secret_value()
        df = channel_utils.fetch_channel_domain_df(pg_url, domains_category)
        channel_ids = df["channel_id"].values.tolist()
        random.shuffle(channel_ids)  # in-place shuffle
        print(
            ",".join(channel_ids)
        )  # Print channel_ids as comma-separated for Airflow XCom
    else:
        if not hasattr(args, "outdir"):
            logger.error("Output directory is required.")
            sys.exit(1)

        if args.task == "fetch_results":
            fetch_results(out_dir=args.outdir, domains_category=domains_category)
        else:
            if not hasattr(args, "channel_ids"):
                logger.error("Channel IDs are required.")
                sys.exit(1)

            channel_ids_list = args.channel_ids.split(",")
            if len(channel_ids_list) == 0:
                logger.warning("No channel IDs specified.")
                sys.exit(0)

            if args.task == "gen_domain_files":
                if not hasattr(args, "seed"):
                    logger.error(
                        "Seed csv file, previous directory and domain mapping are required for gen_domain_files task."
                    )
                    sys.exit(1)

                gen_domain_files(
                    channel_seeds_csv=args.seed,
                    channel_bots_csv=args.bots,
                    channel_ids_list=channel_ids_list,
                    domains_category=domains_category,
                    out_dir=args.outdir,
                )
            elif args.task == "process_domains":
                process_domains(
                    channel_ids_list=channel_ids_list,
                    domains_category=domains_category,
                    out_dir=args.outdir,
                )
            else:
                logger.error(
                    "Invalid task specified. Use 'fetch_domains', 'process_domains' or 'gen_domain_files'."
                )
                sys.exit(1)

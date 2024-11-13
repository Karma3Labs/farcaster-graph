# standard dependencies
import sys
import argparse
import random
from enum import Enum
from pathlib import Path
import os
from typing import Tuple

# local dependencies
import utils
import db_utils
import go_eigentrust
from config import settings
from . import channel_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
import tomlkit as toml

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

class Mode(Enum):
    goserver = 'goserver'
    openrank = 'openrank'

_LT_FILENAME_FORMAT = "localtrust.{cid}.{interval}.{domain}.csv"
_PT_FILENAME_FORMAT = "pretrust.{cid}.{interval}.{domain}.csv"
_TOML_FILENAME_FORMAT = "config.{cid}.{interval}.{domain}.toml"

def write_openrank_files(
    cid: str,
    domain: int,
    interval: int,
    channel_lt_df: pd.DataFrame,
    pretrust_fid_list: list[int],
    out_dir: Path,
): 
    lt_filename = _LT_FILENAME_FORMAT.format(cid=cid, interval=interval, domain=domain)
    logger.info(f"Saving localtrust for channel {cid} to {lt_filename}")
    # Filter out entries where i == j
    channel_lt_df = channel_lt_df[channel_lt_df['i'] != channel_lt_df['j']]
    channel_lt_df.to_csv(os.path.join(out_dir, lt_filename), index=False)

    pt_filename = _PT_FILENAME_FORMAT.format(cid=cid, interval=interval, domain=domain)
    logger.info(f"Saving pretrust for channel {cid} to {pt_filename}")
    # Convert pretrust_fid_list list to a set to remove duplicates
    pt_ids_set = set(pretrust_fid_list)
    pt_len = len(pt_ids_set)
    pretrust = [{'i': fid, 'v': 1/pt_len} for fid in pt_ids_set]
    channel_pt_df = pd.DataFrame(pretrust)
    channel_pt_df.to_csv(os.path.join(out_dir, pt_filename), index=False)

    doc = toml.document()
    doc.add(toml.comment(f"configuration for channel:{cid} interval:{interval}"))
    doc.add(toml.nl())

    domain_section = toml.table()
    domain_section.add("algo_id", 0)
    domain_section.add("trust_owner", settings.OPENRANK_REQ_ADDR)
    domain_section.add("trust_id", domain)
    domain_section.add("seed_owner", settings.OPENRANK_REQ_ADDR)
    domain_section.add("seed_id", domain)
    doc.add("domain", domain_section)
    doc.add(toml.nl())

    sequencer_section = toml.table()
    sequencer_section.add("endpoint", settings.OPENRANK_URL)
    max_result_size = len(set(channel_lt_df['i']) | set(channel_lt_df['j'])) # sub-optimal but good enough
    sequencer_section.add("result_size", max_result_size)
    doc.add("sequencer", sequencer_section)
    doc.add(toml.nl())

    toml_file = os.path.join(
        out_dir, _TOML_FILENAME_FORMAT.format(cid=cid, interval=interval, domain=domain)
    )
    with open(toml_file, "w") as f:
        f.write(toml.dumps(doc))

    return

def process_prev_files(
    cid: str,
    domain: int,
    interval: int,
    channel_lt_df: pd.DataFrame,
    pretrust_fid_list: list[int],
    prev_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    prev_lt_file = os.path.join(
        prev_dir, _LT_FILENAME_FORMAT.format(cid=cid, interval=interval, domain=domain)
    )
    prev_pt_file = os.path.join(
        prev_dir, _PT_FILENAME_FORMAT.format(cid=cid, interval=interval, domain=domain)
    )

    if not (prev_lt_file.exists() and prev_lt_file.exists()):
        logger.warning(f"{prev_dir} is missing previous files for"
                        f" channel {cid} with domain {domain} and interval {interval}")
    
    prev_lt_df = pd.read_csv(prev_lt_file)
    prev_pt_df = pd.read_csv(prev_pt_file)

    # TODO calculate delta

    return channel_lt_df, pretrust_fid_list

def process_channels(
    channel_seeds_csv: Path,
    channel_ids_str: str,
    channel_domains_csv: Path,
    out_dir: Path,
    prev_dir: Path,
):
    # Setup connection pool for querying Warpcast API

    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_ids = channel_ids_str.split(',')
    channel_domain_df = channel_utils.read_channel_domain_csv(channel_domains_csv)
    if len(channel_domain_df[channel_domain_df['channel_id'].isin(channel_ids)]) != len(channel_ids):
        raise Exception(f"Missing channel domains for {set(channel_ids) - set(channel_domain_df['channel_id'].values)}")
    missing_seed_fids = []

    for cid in channel_ids:
        try:
            channel = channel_domain_df[channel_domain_df['channel_id'] == cid]
            if len(channel) == 0:
                raise Exception(f"Missing channel domain for {cid}")
            interval = channel['interval_days'].values[0]
            domain = int(channel['domain'].values[0])

            channel_lt_df, pretrust_fid_list, absent_fids = channel_utils.prep_trust_data(cid, channel_seeds_df, pg_dsn, pg_url, interval)

            if len(channel_lt_df) == 0:
                if interval > 0:
                    logger.info(f"No local trust for channel {cid} for interval {interval}")
                    return {cid: []}
                else:
                    logger.error(f"No local trust for channel {cid} for lifetime engagement")
                    # this is unexpected because if a channel exists there must exist at least one ijv 
                    raise Exception(f"No local trust for channel {cid} for lifetime engagement")
            # Future Feature: keep track and clean up seed fids that have had no engagement in channel
            missing_seed_fids.append({cid: absent_fids})

            channel_lt_df, pretrust_fid_list = process_prev_files(
                cid=cid,
                domain=domain,
                interval=interval,
                channel_lt_df=channel_lt_df,
                pretrust_fid_list=pretrust_fid_list,
                prev_dir=prev_dir
            )
                
            write_openrank_files(
                cid=cid,
                domain=domain,
                interval=interval,
                channel_lt_df=channel_lt_df,
                pretrust_fid_list=pretrust_fid_list,
                out_dir=out_dir
            )
        except Exception as e:
            logger.error(f"failed to process a channel: {cid}: {e}")
            raise e

    logger.info(missing_seed_fids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--csv",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the CSV file. For example, -c /path/to/file.csv",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--task",
        type=str,
        help="task to perform: fetch or process",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--domain_mapping",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the channel id - domain CSV file. For example, -c /path/to/file.csv",
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
    parser.add_argument(
        "-p",
        "--prevdir",
        type=lambda f: Path(f).expanduser().resolve(),
        help="directory for previous run of process_domain task",
        required=False,
    )
    args = parser.parse_args()
    print(args)

    logger.debug('hello main')

    if args.task == 'fetch_domains':
        df = channel_utils.read_channel_domain_csv(args.domain_mapping)
        channel_ids = df["channel_id"].values.tolist()
        random.shuffle(channel_ids) # in-place shuffle
        print(','.join(channel_ids))  # Print channel_ids as comma-separated for Airflow XCom
    elif args.task == 'gen_domain_files':
        if (
            not hasattr(args, "channel_ids")
            or not hasattr(args, "domain_mapping")
            or not hasattr(args, "outdir")
            or not hasattr(args, "prevdir")
        ):
            logger.error("Channel IDs, Domain mapping,"
                            " output directory and previous directory"
                            " are required for gen_domain_files task.")
            sys.exit(1)

        process_channels(
            channel_seeds_csv=args.csv,
            channel_ids_str=args.channel_ids,
            channel_domains_csv=args.domain_mapping,
            out_dir=args.outdir,
            prev_dir=args.prevdir
        )
    else:
        logger.error("Invalid task specified. Use 'fetch_domains' or 'gen_domain_files'.")
        sys.exit(1)
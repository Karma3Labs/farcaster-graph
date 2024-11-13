# standard dependencies
import sys
import argparse
import random
from enum import Enum
from pathlib import Path
import os

# local dependencies
import utils
import db_utils
import go_eigentrust
from config import settings
from . import channel_utils
from . import channel_queries

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

def prep_trust_data(
    cid: str, channel_seeds_df: pd.DataFrame, pg_dsn: str, pg_url: str, interval: int
): 
    host_fids: list = [int(fid) for fid in channel_seeds_df[channel_seeds_df["channel id"] == cid]["seed_fids_list"].values[0]]
    try:
        channel = db_utils.fetch_channel_details(pg_url, channel_id=cid)
        if channel is None:
            logger.error(f"Failed to fetch channel details for channel {cid}: skipping")
            return {cid: []}
        if len(host_fids) == 0:
            lead_fid = channel['leadfid']
            host_fids.append(lead_fid)
            mod_fids = [int(fid) for fid in channel['moderatorfids']]
            host_fids.extend(mod_fids)
    except Exception as e:
        logger.error(f"Failed to fetch channel details for channel {cid}: {e}")
        raise e

    logger.info(f"Channel details: {channel}")
    logger.info(f"Host fids: {set(host_fids)}")

    utils.log_memusage(logger)
    try:
        channel_interactions_df = channel_queries.fetch_interactions_df(
            logger, pg_dsn, channel_url=channel["url"], interval=interval
        )
        channel_interactions_df = channel_interactions_df.rename(columns={'l1rep6rec3m12': 'v'})
        logger.info(utils.df_info_to_string(channel_interactions_df, with_sample=True))
        utils.log_memusage(logger)
    except Exception as e:
        logger.error(f"Failed to fetch channel interactions DataFrame: {e}")
        raise e
        # return {cid: []}

    try:
        fids = db_utils.fetch_channel_casters(pg_dsn=pg_dsn, channel_url=channel['url'])
    except Exception as e:
        logger.error(f"Failed to fetch channel casters for channel {cid}: {e}")
        raise e
        # return {cid: []}

    logger.info(f"Number of channel casters: {len(fids)}")
    if len(fids) > 5:
        logger.info(f"Sample of channel casters: {random.sample(fids, 5)}")
    else:
        logger.info(f"All channel casters: {fids}")

    fids.extend(host_fids)  # host_fids need to be included in the eigentrust compute

    try:
        # filter channel interactions by those following the channel
        channel_lt_df = channel_interactions_df[channel_interactions_df['i'].isin(fids) & channel_interactions_df['j'].isin(fids)]
        logger.info(f"Localtrust: {utils.df_info_to_string(channel_lt_df, with_sample=True)}")
    except Exception as e:
        logger.error(f"Failed to compute local trust for channel {cid}: {e}")
        raise e

    pretrust_fids = list(set(host_fids).intersection(channel_lt_df['i'].values))
    absent_fids = set(host_fids) - set(channel_lt_df['i'].values)
    logger.info(f"Absent Host Fids for the channel: {absent_fids}")
    logger.info(f"Pretrust FIDs: {pretrust_fids}")

    return channel_lt_df, pretrust_fids, absent_fids

def gen_openrank_input(
    cid: str,
    domain: int,
    interval: int,
    channel_lt_df: pd.DataFrame,
    pretrust_fids: list[int],
    out_dir: Path,
): 

    lt_filename = f"localtrust.{cid}.{interval}.{domain}.csv"
    logger.info(f"Saving localtrust for channel {cid} to {lt_filename}")
    # Filter out entries where i == j
    channel_lt_df = channel_lt_df[channel_lt_df['i'] != channel_lt_df['j']]
    channel_lt_df.to_csv(os.path.join(out_dir, lt_filename), index=False)

    pt_filename = f"pretrust.{cid}.{interval}.{domain}.csv"
    logger.info(f"Saving pretrust for channel {cid} to {pt_filename}")
    # Convert pretrust_fids list to a set to remove duplicates
    pt_ids_set = set(pretrust_fids)
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

    with open(os.path.join(out_dir, f"config.{cid}.{interval}.{domain}.toml"), "w") as f:
        f.write(toml.dumps(doc))

    return

def process_channel_goserver(
        cid: str,
        channel_lt_df: pd.DataFrame,
        pretrust_fids: pd.DataFrame,
        pg_url: str,
        interval: int,
) -> dict:
    try:
        scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=pretrust_fids)
    except Exception as e:
        logger.error(f"Failed to compute EigenTrust scores for channel {cid}: {e}")
        raise e

    logger.info(f"go_eigentrust returned {len(scores)} entries")

    if len(scores) == 0:
        if interval > 0:
            logger.info(f"No globaltrust for channel {cid} for interval {interval}")
            return {cid: []}
        else:
            logger.error(f"No globaltrust for channel {cid} for lifetime engagement")
            raise Exception(f"No globaltrust for channel {cid} for lifetime engagement")

    logger.debug(f"Channel user scores: {scores}")

    scores_df = pd.DataFrame(data=scores)
    scores_df['channel_id'] = cid
    scores_df.rename(columns={'i': 'fid', 'v': 'score'}, inplace=True)
    scores_df['rank'] = scores_df['score'].rank(
        ascending=False,
        method='first'
    ).astype(int)
    scores_df['strategy_name'] = f'{interval}d_engagement' if interval > 0 else 'channel_engagement' 
    logger.info(utils.df_info_to_string(scores_df, with_sample=True))
    utils.log_memusage(logger)

    try:
        logger.info(f"Inserting data into the database for channel {cid}")
        db_utils.df_insert_copy(pg_url=pg_url, df=scores_df, dest_tablename=settings.DB_CHANNEL_FIDS)
    except Exception as e:
        logger.error(f"Failed to insert data into the database for channel {cid}: {e}")
        raise e
    return 


def process_channels(
    channel_seeds_csv: Path,
    channel_ids_str: str,
    interval: int = 0,
    mode: Mode = Mode.goserver,
    channel_domains_csv: Path = None,
    out_dir: Path = None,
):
    # Setup connection pool for querying Warpcast API

    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    channel_seeds_df = channel_utils.read_channel_seed_fids_csv(channel_seeds_csv)
    channel_ids = channel_ids_str.split(',')
    if mode == Mode.openrank:
        channel_domain_df = channel_utils.read_channel_domain_csv(channel_domains_csv)
        if len(channel_domain_df[channel_domain_df['channel_id'].isin(channel_ids)]) != len(channel_ids):
            raise Exception(f"Missing channel domains for {set(channel_ids) - set(channel_domain_df['channel_id'].values)}")
    missing_seed_fids = []

    for cid in channel_ids:
        try:
            if mode == Mode.openrank:
                channel = channel_domain_df[channel_domain_df['channel_id'] == cid]
                if len(channel) == 0:
                    raise Exception(f"Missing channel domain for {cid}")
                interval = channel['interval_days'].values[0]
                domain = int(channel['domain'].values[0])

            channel_lt_df, pretrust_fids, absent_fids = prep_trust_data(cid, channel_seeds_df, pg_dsn, pg_url, interval)

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
                
            if mode == Mode.goserver:
                process_channel_goserver(
                    cid=cid,
                    channel_lt_df=channel_lt_df,
                    pretrust_fids=pretrust_fids,
                    pg_url=pg_url,
                    interval=interval,
                )
            elif mode == Mode.openrank:
                gen_openrank_input(
                    cid=cid,
                    domain=domain,
                    interval=interval,
                    channel_lt_df=channel_lt_df,
                    pretrust_fids=pretrust_fids,
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
        "-ids",
        "--channel_ids",
        type=str,
        help="channel IDs for processing, only used for process task",
        required=False,
    )
    parser.add_argument(
        "-int",
        "--interval",
        type=int,
        help="number of days to consider for processing, 0 means lifetime",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--domain_mapping",
        type=lambda f: Path(f).expanduser().resolve(),
        help="path to the channel id - domain CSV file. For example, -c /path/to/file.csv",
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

    logger.debug('hello main')

    if args.task == 'fetch':
        channel_ids = channel_utils.read_channel_ids_csv(args.csv)
        random.shuffle(channel_ids) # in-place shuffle
        print(','.join(channel_ids))  # Print channel_ids as comma-separated for Airflow XCom
    elif args.task == 'fetch_domains':
        df = channel_utils.read_channel_domain_csv(args.domain_mapping)
        channel_ids = df["channel_id"].values.tolist()
        random.shuffle(channel_ids) # in-place shuffle
        print(','.join(channel_ids))  # Print channel_ids as comma-separated for Airflow XCom
    else:
        if not hasattr(args, 'channel_ids'):
            logger.error("Channel IDs are required for processing.")
            sys.exit(1)
        if args.task == 'gen_domain_files':
            if not hasattr(args, 'outdir') or not hasattr(args, 'domain_mapping'):
                logger.error("Domain mapping and output directory are required for gen_domain_files task.")
                sys.exit(1)
            process_channels(
                channel_seeds_csv=args.csv,
                channel_ids_str=args.channel_ids,
                mode=Mode.openrank,
                channel_domains_csv=args.domain_mapping,
                out_dir=args.outdir
            )
        elif args.task == 'process':
            if not hasattr(args, 'interval'):
                logger.error("Interval is required for processing.")
                sys.exit(1)
            process_channels(
                channel_seeds_csv=args.csv,
                channel_ids_str=args.channel_ids,
                interval=args.interval,
                mode=Mode.goserver,
            )
        else:
            logger.error("Invalid task specified. Use 'fetch' or 'process'.")
            sys.exit(1)
from pathlib import Path
import random

import utils
import db_utils
from . import channel_queries

from loguru import logger
import pandas as pd

def read_channel_seed_fids_csv(csv_path:Path) -> pd.DataFrame:
    try:
        seeds_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info 
        # ... but channel id should not be empty
        seeds_df = seeds_df.dropna(subset = ['channel id'])
        seeds_df = seeds_df.drop_duplicates(subset=['channel id'], keep='last')
        seeds_df.rename(columns={"Seed Peers FIDs": "seed_peers"}, inplace=True)
        seeds_df = seeds_df[["channel id", "seed_peers"]]
        seeds_df["seed_peers"] = seeds_df["seed_peers"].astype(str)
        seeds_df["seed_fids_list"] = seeds_df.apply(lambda row: [] if row["seed_peers"] == "nan" else row["seed_peers"].split(","), axis=1)
        seeds_df['channel id'] = seeds_df['channel id'].str.lower()
        return seeds_df
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

def read_channel_domain_csv(csv_path:Path, channel_ids:list[str]=None) -> pd.DataFrame:
    try:
        domains_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info 
        # ... but channel_id, interval_days and domain should not be empty
        domains_df = domains_df.dropna(subset = ['channel_id', 'interval_days', 'domain'])

        if any(domains_df['domain'].duplicated()):
            raise Exception(f"Duplicate domains in {csv_path}: {domains_df[domains_df['domain'].duplicated()]}")
        if any(domains_df['channel_id'].duplicated()):
            raise Exception(f"Duplicate channels in {csv_path}: {domains_df[domains_df['channel_id'].duplicated()]}")
        domains_df = domains_df[['channel_id', 'interval_days', 'domain']]
        domains_df['channel_id'] = domains_df['channel_id'].str.lower()
        domains_df['interval_days'] = domains_df['interval_days'].astype(int)
        if channel_ids:
            domains_df = domains_df[domains_df['channel_id'].isin(channel_ids)]
            missing_channels = set(channel_ids) - set(domains_df['channel_id'].values)
            if len(missing_channels) > 0:
                raise Exception(f"Missing channel domains for {missing_channels}")
        return domains_df
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

def read_channel_ids_csv(csv_path:Path) -> list:
    try:
        channels_df = pd.read_csv(csv_path)
        channels_df = channels_df.dropna(subset = ['channel id'])
        channels_df = channels_df.drop_duplicates(subset=['channel id'], keep='last')
        channels_df = channels_df[["channel id"]]
        channels_df['channel id'] = channels_df['channel id'].str.lower()
        channel_ids = channels_df["channel id"].values.tolist()
        return channel_ids
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

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

def pretrust_list_to_df(pretrust_fid_list: list[int]) -> pd.DataFrame:
    # Convert pretrust_fid_list list to a set to remove duplicates
    pt_ids_set = set(pretrust_fid_list)
    pt_len = len(pt_ids_set)
    pretrust_dict = [{'i': fid, 'v': 1/pt_len} for fid in pt_ids_set]
    return pd.DataFrame(pretrust_dict)

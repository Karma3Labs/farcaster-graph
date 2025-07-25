import random
from pathlib import Path

import pandas as pd
from loguru import logger

import db_utils
import go_eigentrust
import utils

from . import channel_db_utils, channel_queries


def read_channel_seed_fids_csv(csv_path: Path) -> pd.DataFrame:
    try:
        seeds_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info
        # ... but channel id should not be empty
        seeds_df = seeds_df.dropna(subset=["channel id"])
        seeds_df = seeds_df.drop_duplicates(subset=["channel id"], keep="last")
        seeds_df.rename(columns={"Seed Peers FIDs": "seed_peers"}, inplace=True)
        seeds_df = seeds_df[["channel id", "seed_peers"]]
        seeds_df["seed_peers"] = seeds_df["seed_peers"].astype(str)
        seeds_df["seed_fids_list"] = seeds_df.apply(
            lambda row: (
                [] if row["seed_peers"] == "nan" else row["seed_peers"].split(",")
            ),
            axis=1,
        )
        seeds_df["channel id"] = seeds_df["channel id"].str.lower()
        return seeds_df
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e


def read_channel_bot_fids_csv(csv_path: Path) -> pd.DataFrame:
    try:
        bots_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info
        # ... but channel id should not be empty
        bots_df = bots_df.dropna(subset=["FID"])
        bots_df = bots_df.drop_duplicates(subset=["FID"], keep="last")
        return bots_df
    except Exception as e:
        logger.error(f"Failed to read bot data from CSV: {e}")
        raise e


def read_trending_channel_ids_csv(csv_path: Path) -> pd.DataFrame:
    try:
        # use pandas to read csv for convenience and easy data cleaning
        cid_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info
        # ... but channel id should not be empty
        cid_df = cid_df.drop_duplicates(keep="last")
        return cid_df
    except Exception as e:
        logger.error(f"Failed to read bot data from CSV: {e}")
        raise e


def fetch_channels_for_category_df(pg_url: str, category: str) -> pd.DataFrame:
    try:
        channels_df = db_utils.fetch_channels_for_category(pg_url, category)
        if len(channels_df) == 0:
            raise Exception(f"No channels found for category {category}")
        return channels_df
    except Exception as e:
        logger.error(f"Failed to read channel data from DB: {e}")
        raise e


def read_channel_ids_csv(csv_path: Path) -> list:
    try:
        channels_df = pd.read_csv(csv_path)
        channels_df = channels_df.dropna(subset=["channel id"])
        channels_df = channels_df.drop_duplicates(subset=["channel id"], keep="last")
        channels_df = channels_df[["channel id"]]
        channels_df["channel id"] = channels_df["channel id"].str.lower()
        channel_ids = list(set(channels_df["channel id"].values.tolist()))
        return channel_ids
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e


def prep_trust_data(
    cid: str,
    channel_seeds_df: pd.DataFrame,
    channel_bots_df: pd.DataFrame,
    pg_dsn: str,
    pg_url: str,
    interval: int,
):
    # channel_seeds_df["seed_fids_list"].values returns [["fid1","fid2"]]
    if cid in channel_seeds_df["channel id"].values:
        host_fids: list = [
            int(fid)
            for fid in channel_seeds_df[channel_seeds_df["channel id"] == cid][
                "seed_fids_list"
            ].values[0]
        ]
    else:
        host_fids = []
    bot_fids = channel_bots_df["FID"].values.tolist()
    try:
        channel = db_utils.fetch_channel_details(pg_url, channel_id=cid)
        if channel is None:
            logger.error(f"Failed to fetch channel details for channel {cid}: skipping")
            return {cid: []}
        if len(host_fids) == 0:
            lead_fid = channel["leadfid"]
            host_fids.append(lead_fid)
            mod_fids = [int(fid) for fid in channel["moderatorfids"]]
            host_fids.extend(mod_fids)
        logger.info(
            f"Removing bot fids {bot_fids} from host fids {host_fids} for channel {cid}: "
            f"{set.intersection(set(host_fids), set(bot_fids))}"
        )
        host_fids = list(set(host_fids) - set(bot_fids))
    except Exception as e:
        logger.error(f"Failed to fetch channel details for channel {cid}: {e}")
        raise e

    logger.info(f"Channel details: {channel}")
    logger.info(f"Host fids: {host_fids}")

    utils.log_memusage(logger)
    try:
        channel_interactions_df = channel_queries.fetch_interactions_df(
            logger,
            pg_dsn,
            channel_url=channel["url"],
            channel_id=channel["id"],
            interval=interval,
        )
        channel_interactions_df = channel_interactions_df.rename(
            columns={"l1rep6rec3m12": "v"}
        )
        logger.info(utils.df_info_to_string(channel_interactions_df, with_sample=True))
        utils.log_memusage(logger)
    except Exception as e:
        logger.error(f"Failed to fetch channel interactions DataFrame: {e}")
        raise e
        # return {cid: []}

    try:
        # TODO should this be restricted to members or followers instead of casters ?
        fids = channel_db_utils.fetch_channel_casters(
            logger=logger, pg_dsn=pg_dsn, channel_url=channel["url"]
        )
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
        # filter channel interactions by those casting in the channel
        # ...F1 follows F2 is global and not channel specific.
        # ...So, we need to filter by F1 and F2 being in the channel
        channel_lt_df = channel_interactions_df[
            channel_interactions_df["i"].isin(fids)
            & channel_interactions_df["j"].isin(fids)
        ]
        logger.info(
            f"Localtrust: {utils.df_info_to_string(channel_lt_df, with_sample=True)}"
        )
    except Exception as e:
        logger.error(f"Failed to compute local trust for channel {cid}: {e}")
        raise e

    pretrust_fids = list(set(host_fids).intersection(channel_lt_df["i"].values))
    absent_fids = list(set(host_fids) - set(channel_lt_df["i"].values))
    logger.info(f"Absent Host Fids for the channel: {absent_fids}")
    logger.info(f"Pretrust FIDs: {pretrust_fids}")

    return channel_lt_df, pretrust_fids, absent_fids


def pretrust_list_to_df(pretrust_fid_list: list[int]) -> pd.DataFrame:
    # Convert pretrust_fid_list list to a set to remove duplicates
    pt_ids_set = set(pretrust_fid_list)
    pt_len = len(pt_ids_set)
    pretrust_dict = [{"i": fid, "v": 1 / pt_len} for fid in pt_ids_set]
    return pd.DataFrame(pretrust_dict)


def compute_goeigentrust(
    cid: str,
    channel_lt_df: pd.DataFrame,
    pretrust_fids: pd.DataFrame,
    interval: int,
) -> pd.DataFrame:
    try:
        scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=pretrust_fids)
    except Exception as e:
        logger.error(f"Failed to compute EigenTrust scores for channel {cid}: {e}")
        raise e

    logger.info(f"go_eigentrust returned {len(scores)} entries")

    if len(scores) == 0:
        if interval > 0:
            logger.info(f"No globaltrust for channel {cid} for interval {interval}")
            return None
        else:
            logger.error(f"No globaltrust for channel {cid} for lifetime engagement")
            raise Exception(f"No globaltrust for channel {cid} for lifetime engagement")

    logger.debug(f"Channel user scores: {scores}")

    scores_df = pd.DataFrame(data=scores)
    scores_df["channel_id"] = cid
    scores_df.rename(columns={"i": "fid", "v": "score"}, inplace=True)
    scores_df["rank"] = (
        scores_df["score"].rank(ascending=False, method="first").astype(int)
    )
    scores_df["strategy_name"] = (
        f"{interval}d_engagement" if interval > 0 else "channel_engagement"
    )
    logger.info(utils.df_info_to_string(scores_df, with_sample=True))
    utils.log_memusage(logger)
    return scores_df

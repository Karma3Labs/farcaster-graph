from pathlib import Path

from loguru import logger
import pandas as pd

def read_channel_seed_fids_csv(csv_path:Path) -> pd.DataFrame:
    try:
        seeds_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info 
        # ... but channel id should not be empty
        seeds_df = seeds_df.dropna(subset = ['channel id'])
        seeds_df.rename(columns={"Seed Peers FIDs": "seed_peers"}, inplace=True)
        seeds_df = seeds_df[["channel id", "seed_peers"]]
        seeds_df["seed_peers"] = seeds_df["seed_peers"].astype(str)
        seeds_df["seed_fids_list"] = seeds_df.apply(lambda row: [] if row["seed_peers"] == "nan" else row["seed_peers"].split(","), axis=1)
        seeds_df['channel id'] = seeds_df['channel id'].str.lower()
        return seeds_df
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

def read_channel_domain_csv(csv_path:Path) -> pd.DataFrame:
    try:
        domains_df = pd.read_csv(csv_path)
        # csv can have extra columns for comments or other info 
        # ... but channel_id, interval_days and domain should not be empty
        domains_df = domains_df.dropna(subset = ['channel_id', 'interval_days', 'domain'])
        domains_df = domains_df[['channel_id', 'interval_days', 'domain']]
        domains_df['channel_id'] = domains_df['channel_id'].str.lower()
        domains_df['interval_days'] = domains_df['interval_days'].astype(int)
        return domains_df
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

def read_channel_ids_csv(csv_path:Path) -> list:
    try:
        channels_df = pd.read_csv(csv_path)
        channels_df = channels_df.dropna(subset = ['channel id'])
        channels_df = channels_df[["channel id"]]
        channels_df['channel id'] = channels_df['channel id'].str.lower()
        channel_ids = channels_df["channel id"].values.tolist()
        return channel_ids
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        raise e

# standard dependencies
import sys
import argparse
import random

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

def process_channel(
        cid: str,
        channel_data: pd.DataFrame,
        pg_dsn: str,
        pg_url: str,
        interval: int,
) -> dict:
    host_fids: list = [int(fid) for fid in channel_data[channel_data["channel id"] == cid]["seed_fids_list"].values[0]]
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
        channel_interactions_df = channel_queries.fetch_interactions_df(logger, pg_dsn, channel_url=channel['url'], interval=interval)
        channel_interactions_df = channel_interactions_df.rename(columns={'l1rep6rec3m12': 'v'})
        logger.info(utils.df_info_to_string(channel_interactions_df, with_sample=True))
        utils.log_memusage(logger)
    except Exception as e:
        logger.error(f"Failed to fetch channel interactions DataFrame: {e}")
        raise e
        # return {cid: []}

    try:
        fids = db_utils.fetch_channel_participants(pg_dsn=pg_dsn, channel_url=channel['url'])
    except Exception as e:
        logger.error(f"Failed to fetch channel participants for channel {cid}: {e}")
        raise e
        # return {cid: []}

    logger.info(f"Number of channel followers: {len(fids)}")
    if len(fids) > 5:
        logger.info(f"Sample of channel followers: {random.sample(fids, 5)}")
    else:
        logger.info(f"All channel followers: {fids}")

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

    if len(channel_lt_df) == 0:
        logger.error(f"No local trust for channel {cid}")
        raise Exception(f"No local trust for channel {cid}")

    try:
        scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=pretrust_fids)
    except Exception as e:
        logger.error(f"Failed to compute EigenTrust scores for channel {cid}: {e}")
        raise e

    logger.info(f"go_eigentrust returned {len(scores)} entries")
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
        # db_utils.df_insert_copy(pg_url=pg_url, df=scores_df, dest_tablename=settings.DB_CHANNEL_FIDS)
    except Exception as e:
        logger.error(f"Failed to insert data into the database for channel {cid}: {e}")
        raise e

    return {cid: absent_fids}


def process_channels(csv_path: str, channel_ids_str: str, interval: int):
    # Setup connection pool for querying Warpcast API

    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    pg_url = settings.POSTGRES_URL.get_secret_value()

    channel_data = channel_utils.read_channel_seed_fids_csv(csv_path)
    channel_ids = channel_ids_str.split(',')
    missing_seed_fids = []

    for cid in channel_ids:
        try:
            result = process_channel(cid, channel_data, pg_dsn, pg_url, interval)
            missing_seed_fids.append(result)
        except Exception as e:
            logger.error(f"failed to process a channel: {cid}: {e}")
            raise e

    logger.info(missing_seed_fids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", type=str, help="path to the CSV file. For example, -c /path/to/file.csv",
                        required=True)
    parser.add_argument("-t", "--task", type=str, help="task to perform: fetch or process", required=True)
    parser.add_argument("-ids", "--channel_ids", type=str,
                        help="channel IDs for processing, only used for process task", required=False)
    parser.add_argument("-int", "--interval", type=int,
                        help="number of days to consider for processing, 0 means lifetime", required=False)
    
    args = parser.parse_args()
    print(args)

    logger.debug('hello main')

    if args.task == 'fetch':
        channel_ids = channel_utils.read_channel_ids_csv(args.csv)
        random.shuffle(channel_ids) # in-place shuffle
        print(','.join(channel_ids))  # Print channel_ids as comma-separated for Airflow XCom
    elif args.task == 'process':
        if hasattr(args, 'channel_ids') and hasattr(args, 'interval'):
            process_channels(args.csv, args.channel_ids, args.interval)
        else:
            logger.error("Channel IDs and interval are required for processing.")
            sys.exit(1)
    else:
        logger.error("Invalid task specified. Use 'fetch' or 'process'.")

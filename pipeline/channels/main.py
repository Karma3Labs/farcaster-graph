# standard dependencies
import sys
import argparse
import random

import pandas as pd
# local dependencies
from config import settings
import utils
import db_utils
import go_eigentrust
from timer import Timer
from . import channel_utils
from . import compute_trust

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
import niquests
from urllib3.util import Retry

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

@Timer(name="main")
def main(csv_path: str, pg_dsn: str, pg_url: str):
    # Setup connection pool for querying Warpcast API
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods=['GET']
    )
    http_session = niquests.Session(retries=retries)

    # Read the channel master CSV for channel_ids
    try:
        channel_data = channel_utils.get_seed_fids_from_csv(csv_path)
    except Exception as e:
        logger.error(f"Failed to read channel data from CSV: {e}")
        sys.exit(1)

    # Process each channel
    missing_seed_fids = []
    for cid in channel_data["channel id"].values:
        try:
            channel = channel_utils.fetch_channel(http_session=http_session, channel_id=cid)
            host_fids = list(set(int(fid) for fid in channel_data[channel_data["channel id"] == cid]["seed_fids_list"].values[0]))
        except Exception as e:
            logger.error(f"Failed to fetch channel details for channel {cid}: {e}")
            continue

        logger.info(f"Channel details: {channel}")

        utils.log_memusage(logger)
        try:
            global_lt_df = compute_trust._fetch_interactions_df(logger, pg_dsn, channel_url=channel.project_url)
            global_lt_df = global_lt_df.rename(columns={'l1rep6rec3m12': 'v'})
            logger.info(utils.df_info_to_string(global_lt_df, with_sample=True))
            utils.log_memusage(logger)
        except Exception as e:
            logger.error(f"Failed to fetch global interactions DataFrame: {e}")
            continue

        try:
            fids = db_utils.fetch_channel_participants(pg_dsn=pg_dsn, channel_url=channel.project_url)
        except Exception as e:
            logger.error(f"Failed to fetch channel participants for channel {cid}: {e}")
            continue

        logger.info(f"Number of channel followers: {len(fids)}")
        if len(fids) > 5:
            logger.info(f"Sample of channel followers: {random.sample(fids, 5)}")
        else:
            logger.info(f"All channel followers: {fids}")

        fids.extend(host_fids)  # host_fids need to be included in the eigentrust compute

        with Timer(name="channel_localtrust"):
            try:
                channel_lt_df = global_lt_df[global_lt_df['i'].isin(fids) & global_lt_df['j'].isin(fids)]
                logger.info(utils.df_info_to_string(channel_lt_df, with_sample=True))
            except Exception as e:
                logger.error(f"Failed to compute local trust for channel {cid}: {e}")
                continue

        present_fids = list(set(host_fids).intersection(channel_lt_df['i'].values))
        absent_fids = list(set(host_fids) - set(channel_lt_df['i'].values))
        logger.info(f"Absent Fids for the channel: {absent_fids}")
        missing_seed_fids.append({cid: absent_fids})

        if len(channel_lt_df) == 0:
            logger.error(f"No local trust for channel {cid}")
            continue

        with Timer(name="go_eigentrust"):
            try:
                scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=present_fids)
            except Exception as e:
                logger.error(f"Failed to compute EigenTrust scores for channel {cid}: {e}")
                continue

        logger.info(f"go_eigentrust returned {len(scores)} entries")
        logger.debug(f"Channel user scores: {scores}")

        scores_df = pd.DataFrame(data=scores)
        scores_df['channel_id'] = cid
        scores_df.rename(columns={'i': 'fid', 'v': 'score'}, inplace=True)
        scores_df['rank'] = scores_df['score'].rank(
            ascending=False,
            method='first'
        ).astype(int)
        scores_df['strategy_name'] = 'channel_engagement'
        logger.info(utils.df_info_to_string(scores_df, with_sample=True))
        utils.log_memusage(logger)

        with Timer(name="insert_db"):
            try:
                logger.info(f"insert_db")
                db_utils.df_insert_copy(pg_url=pg_url, df=scores_df, dest_tablename=settings.DB_CHANNEL_FIDS)
            except Exception as e:
                logger.error(f"Failed to insert data into the database for channel {cid}: {e}")

    logger.info(missing_seed_fids)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", type=str, help="path to the CSV file. For example, -c /path/to/file.csv", required=True)

    args = parser.parse_args()
    print(args)

    load_dotenv()
    print(settings)

    logger.debug('hello main')
    main(
        csv_path=args.csv,
        pg_dsn=settings.POSTGRES_DSN.get_secret_value(),
        pg_url=settings.POSTGRES_URL.get_secret_value()
    )

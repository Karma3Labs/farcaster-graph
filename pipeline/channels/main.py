# standard dependencies
import sys
import argparse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

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
import pandas
import niquests
from urllib3.util import Retry

# Load environment variables
load_dotenv()

# perf optimization to avoid copies unless there is a write on shared data
pandas.set_option("mode.copy_on_write", True)

# Initialize logger
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

def process_channel(cid, channel_data, http_session, pg_dsn):
    try:
        channel = channel_utils.fetch_channel(http_session=http_session, channel_id=cid)

        host_fids = channel_data[channel_data["channel id"] == cid]["seed_fids_list"].values[0]
        host_fids = list(set([int(fid) for fid in host_fids]))

        logger.info(f"Channel details: {channel}")

        utils.log_memusage(logger)
        global_lt_df = compute_trust._fetch_interactions_df(logger, pg_dsn, channel_url=channel.project_url)
        global_lt_df = global_lt_df.rename(columns={'l1rep6rec3m12': 'v'})
        logger.info(utils.df_info_to_string(global_lt_df, with_sample=True))
        utils.log_memusage(logger)

        fids = db_utils.fetch_channel_participants(pg_dsn=pg_dsn, channel_url=channel.project_url)

        logger.info(f"Number of channel followers: {len(fids)}")
        logger.info(f"Sample of channel followers: {random.sample(fids, 5)}")

        fids.extend(host_fids)  # host_fids need to be included in the eigentrust compute

        def _get_scores(global_lt_df, fids):
            with Timer(name="channel_localtrust"):
                channel_lt_df = global_lt_df[global_lt_df['i'].isin(fids) & global_lt_df['j'].isin(fids)]
                logger.info(utils.df_info_to_string(channel_lt_df, with_sample=True))

            present_fids = list(set(host_fids).intersection(channel_lt_df['i'].values))
            absent_fids = list(set(host_fids) - set(channel_lt_df['i'].values))
            logger.info(f"Absent Fids for the channel: {absent_fids}")

            if len(channel_lt_df) == 0:
                logger.error(f"No localtrust for channel {cid}")
                return None, absent_fids

            with Timer(name="go_eigentrust"):
                scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=present_fids)
            return scores, absent_fids

        scores, absent_fids = _get_scores(global_lt_df, fids)
        if scores is None:
            return None, absent_fids

        logger.info(f"go_eigentrust returned {len(scores)} entries")
        logger.debug(f"channel user scores:{scores}")

        scores_df = pandas.DataFrame(data=scores)
        scores_df['channel_id'] = cid
        scores_df.rename(columns={'i': 'fid', 'v': 'score'}, inplace=True)
        scores_df['rank'] = scores_df['score'].rank(
            ascending=False,  # highest score will get rank 1
            method='first'  # if there is a tie, then first entry will get rank 1
        ).astype(int)
        scores_df['strategy_name'] = 'channel_engagement'
        logger.info(utils.df_info_to_string(scores_df, with_sample=True))
        utils.log_memusage(logger)

        # with Timer(name="insert_db"):
        #     db_utils.df_insert_copy(pg_url=pg_url,
        #                             df=scores_df,
        #                             dest_tablename=settings.DB_CHANNEL_FIDS)

        return scores_df, absent_fids
    except Exception as e:
        logger.error(f"Error processing channel {cid}: {e}")
        return None, []

@Timer(name="main")
def main(
        csv_path: str,
        pg_dsn: str,
        pg_url: str
):
    try:
        # setup connection pool for querying warpcast api
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods={'GET'},
        )
        http_session = niquests.Session(retries=retries)

        # Read the channel master csv for channel_ids
        channel_data = channel_utils.get_seed_fids_from_csv(csv_path)

        # Get all channel IDs
        channel_ids = list(channel_data["channel id"].values)

        missing_seed_fids = []

        # Parallel processing with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_channel, cid, channel_data, http_session, pg_dsn): cid for cid in channel_ids}
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    scores_df, absent_fids = future.result()
                    if scores_df is not None:
                        # Here you can handle the resulting DataFrame (e.g., save to DB)
                        pass
                    if absent_fids:
                        missing_seed_fids.append({cid: absent_fids})
                except Exception as e:
                    logger.error(f"Error processing channel {cid}: {e}")

        logger.info(missing_seed_fids)
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv",
                        type=str,
                        help="path to the CSV file. For example, -c /path/to/file.csv",
                        required=True)

    args = parser.parse_args()
    print(args)

    logger.debug('hello main')
    main(
        csv_path=args.csv,
        pg_dsn=settings.POSTGRES_DSN.get_secret_value(),
        pg_url=settings.POSTGRES_URL.get_secret_value())

# standard dependencies
import sys
import argparse
import random
from pathlib import Path

# local dependencies
from config import settings
import utils, db_utils
from timer import Timer
from . import channel_utils
from . import go_eigentrust
from . import compute_trust

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas
import niquests
from urllib3.util import Retry

# perf optimization to avoid copies unless there is a write on shared data
pandas.set_option("mode.copy_on_write", True)

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
def main(
        channel_ids: list[str],
        pg_dsn: str,
        pg_url: str
):
    # setup connection pool for querying warpcast api

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={'GET'},
    )
    http_session = niquests.Session(retries=retries)

    # for each channel, fetch channel details,
    # take a slice of localtrust and run go-eigentrust
    for cid in channel_ids:
        channel = channel_utils.fetch_channel(http_session=http_session,
                                              channel_id=cid)
        logger.info(f"Channel details: {channel}")

        utils.log_memusage(logger)
        global_lt_df = compute_trust._fetch_interactions_df(logger, 
                                                            pg_dsn, 
                                                            channel_url=channel.project_url)
        global_lt_df = global_lt_df.rename(columns={'l1rep6rec3m12': 'v'})
        logger.info(utils.df_info_to_string(global_lt_df, with_sample=True))
        utils.log_memusage(logger)
        # fids = channel_utils.fetch_channel_followers(http_session=http_session,
        #                                              channel_id=cid)
        fids = db_utils.fetch_channel_participants(pg_dsn=pg_dsn,
                                                   channel_url=channel.project_url)

        logger.info(f"Number of channel followers: {len(fids)}")
        logger.info(f"Sample of channel followers: {random.sample(fids, 5)}")

        fids.extend(channel.host_fids)  # host_fids need to be included in the eigentrust compute

        with Timer(name="channel_localtrust"):
            # TODO Perf - fids should be a 'set' and not a 'list'
            # TODO Perf - filter using 'query' instead of 'isin'
            # TODO Perf - install 'numexpr' to speed up pandas
            channel_lt_df = global_lt_df[global_lt_df['i'].isin(fids) & global_lt_df['j'].isin(fids)]
            logger.info(utils.df_info_to_string(channel_lt_df, with_sample=True))

        if len(channel_lt_df) == 0:
            logger.error(f"No localtrust for channel {cid}")
            continue

        with Timer(name="go_eigentrust"):
            scores = go_eigentrust.get_scores(lt_df=channel_lt_df, pt_ids=channel.host_fids)

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

        with Timer(name="insert_db"):
            db_utils.df_insert_copy(pg_url=pg_url,
                                    df=scores_df,
                                    dest_tablename=settings.DB_CHANNEL_FIDS)
    # end of for loop


# How to run this program:
# cd farcaster-graph/pipeline
# source .venv/bin/activate
# python3 -m channels.main -i degen farcaster base -l ../serve/samples/fc_engagement_fid_df.pkl
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ids",
                        nargs='+',
                        help="list of channel ids. For example, -i farcaster base degen",
                        required=True)

    args = parser.parse_args()
    print(args)

    load_dotenv()
    print(settings)

    logger.debug('hello main')
    main(
        channel_ids=args.ids,
        pg_dsn=settings.POSTGRES_DSN.get_secret_value(),
        pg_url=settings.POSTGRES_URL.get_secret_value())

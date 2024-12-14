# standard dependencies
import sys
import argparse
from enum import Enum
import urllib.parse
from urllib3.util import Retry

# local dependencies
from config import settings
from . import channel_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import niquests
from niquests.auth import HTTPBasicAuth

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)

load_dotenv()

class Scope(Enum):
  airdrop = 'airdrop'
  daily = 'daily'

class Task(Enum):
  prep = 'prep'
  distrib = 'distrib'
  verify = 'verify'

def prepare_for_distribution(scope: Scope, reason: str):
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = 180_000
    is_airdrop = True if scope == Scope.airdrop else False
    channels_list = channel_db_utils.fetch_channels_tokens_status(logger, pg_dsn, sql_timeout_ms)
    logger.info(f"Channel token status: {channels_list}")
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    connect_timeout_s = 5.0
    read_timeout_s = 30.0
    with niquests.Session(retries=retries) as s:
        # reuse TCP connection for multiple scm requests
        s.auth = HTTPBasicAuth(settings.CURA_SCMGR_USERNAME, settings.CURA_SCMGR_PASSWORD.get_secret_value())
        for channel_id, token_status in channels_list:
            if not token_status:
                logger.info(f"Channel '{channel_id}' has no distributions. Checking token launch status.")
                try:
                    response = s.get(
                        urllib.parse.urljoin(
                            settings.CURA_SCMGR_URL,
                            f"/token/lookupTokenForChannel/{channel_id}",
                        ),
                        timeout=(connect_timeout_s, read_timeout_s),
                    )
                    if response.status_code == 200:
                        logger.info(f"Channel '{channel_id}' has token. Prepping distribution.")
                    elif response.status_code == 404:
                        logger.warning(f"404 Error: Skipping channel {channel_id} :{response.reason}")
                        continue
                except Exception as e:
                    logger.error(f"Failed to call smartcontractmgr: {e}")
                    raise e
            logger.info(f"Prepping distribution for channel '{channel_id}'")
            channel_db_utils.insert_tokens_log(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
                channel_id=channel_id,
                reason=reason,
                is_airdrop=is_airdrop,
            )


def distribute_tokens():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = settings.POSTGRES_TIMEOUT_SECS * 1000
    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    with niquests.Session(retries=retries) as s:
        # reuse TCP connection for multiple scm requests
        s.auth = HTTPBasicAuth(settings.CURA_SCMGR_USERNAME, settings.CURA_SCMGR_PASSWORD.get_secret_value())
        while True:
            # todo maybe? - parallelize this ? dbpool, http pool ?
            channel_distributions = channel_db_utils.fetch_distributions_for_channel(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
            )
            if channel_distributions is None:
                logger.info("No more channels to distribute.")
                # break
                return
            channel_id = channel_distributions[0]
            distributions = channel_distributions[1]
            dist_id = channel_db_utils.get_next_dist_sequence (
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
            )
            scm_distribute(
                http_session=s,
                dist_id=dist_id,
                channel_id=channel_id,
                distributions=distributions,
            )
            logger.info(f"Distributed tokens for channel '{channel_id}'")
            # WARNING: big assumption that no new inserts have happened in the meanwhile
            # ... todo maybe? - move to a select for update  2-phase commit model
            channel_db_utils.update_distribution_status(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
                dist_id=dist_id,
                channel_id=channel_id,
            )
            # TODO token balances should be updated only after verify 
            channel_db_utils.update_token_bal(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
                dist_id=dist_id,
                channel_id=channel_id,
            )

def scm_distribute(http_session, dist_id, channel_id, distributions):
    logger.info(
        f"call smartcontractmgr {dist_id} for channel '{channel_id}'"
        f" with distributions {distributions}"
    )
    payload = {'distributionId': dist_id, 'channelId': channel_id, 'distributions': distributions}
    logger.info(f"payload: {payload}")
    connect_timeout_s = 5.0
    read_timeout_s = 60.0
    try:
        response = http_session.post(
            urllib.parse.urljoin(settings.CURA_SCMGR_URL,"/distribution/"),
            json=payload,
            timeout=(connect_timeout_s, read_timeout_s)
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to call smartcontractmgr: {e}")
        # raise e 
        

def verify_distribution():
    # TODO fetch 'submitted' distributions from db
    # TODO call smartcontractmgr for status of distributions
    # TODO update k3l_channel_tokens_bal
    pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--task",
        choices=list(Task),
        type=Task,
        help="task to perform: prepare or distribute or verify",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--scope",
        help="airdrop or daily",
        required=False,
        choices=list(Scope),
        type=Scope,
    )
    parser.add_argument(
        "-r",
        "--reason",
        help="reason for distribution",
        required=False,
        type=str,
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.task == Task.prep:
        logger.info('hello prepare')
        if not hasattr(args, "scope") or not hasattr(args, "reason"):
            logger.error("Scope and reason are required for preparing distribution.")
            sys.exit(1)
        prepare_for_distribution(args.scope, args.reason)
    elif args.task == Task.distrib:
        logger.info('hello distribute')
        distribute_tokens()
    elif args.task == Task.verify:
        logger.info('hello verify')
        verify_distribution()
    else:
        raise Exception(f"Unknown task {args.task}")

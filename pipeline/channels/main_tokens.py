# standard dependencies
import sys
import argparse
from enum import Enum
import urllib.parse
from urllib3.util import Retry
import random

# local dependencies
from config import settings
from . import channel_db_utils
from .channel_db_utils import TokenDistStatus

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
    insert_timeout_ms = 120_000
    is_airdrop = True if scope == Scope.airdrop else False
    channels_list = channel_db_utils.fetch_rewards_config_list(logger, pg_dsn, settings.POSTGRES_TIMEOUT_MS)
    logger.debug(f"Channel token status: {channels_list}")
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
        for channel in channels_list:
            channel_id = channel['channel_id']
            token_status = channel['is_tokens']
            if not token_status:
                # In Postgres, we don't know if channel token is launched;
                # ...let's query Cura Smart Contract Manager.
                try:
                    path = f"/token/lookupTokenForChannel/{channel_id}"
                    logger.info(f"Channel '{channel_id}' has no distributions. Checking :{path}")
                    response = s.get(
                        urllib.parse.urljoin(settings.CURA_SCMGR_URL,path),
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                        timeout=(connect_timeout_s, read_timeout_s),
                    )
                    if response.status_code == 200:
                        channel_token = response.json()
                        token_address = channel_token.get('tokenAddress')
                        # TODO get token supply details from SCM
                        if token_address:
                            logger.info(f"Channel '{channel_id}' has token {channel_token}.")
                            channel_db_utils.update_channel_token_status(
                                logger,
                                pg_dsn,
                                settings.POSTGRES_TIMEOUT_MS,
                                channel_id,
                                True,
                            )
                        else:
                            logger.info(f"Channel '{channel_id}' token not fully launched: {channel_token}.")
                    elif response.status_code == 404:
                        logger.warning(f"404 Error: Skipping channel {channel_id} :{response.reason}")
                        continue
                except Exception as e:
                    logger.error(f"Failed to call smartcontractmgr: {e}")
                    raise e
            # We know from Postgres or from SCM that channel token is launched;
            # ...let's prepare for distributing tokens based on recent balance update timestamp.
            logger.info(f"Prepping distribution for channel '{channel_id}'")
            channel_db_utils.insert_tokens_log(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=insert_timeout_ms,
                channel_id=channel_id,
                reason=reason,
                is_airdrop=is_airdrop,
            )


def distribute_tokens():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    upsert_timeout_ms = 180_000
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
            
            channel_distributions = channel_db_utils.fetch_distributions_one_channel(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=settings.POSTGRES_TIMEOUT_MS,
            )
            if channel_distributions is None:
                logger.info("No more channels to distribute.")
                # break
                return
            channel_id = channel_distributions[0]
            dist_id = channel_distributions[1]
            distributions = channel_distributions[2]
            channel_config = channel_db_utils.fetch_rewards_config_list(
                logger, pg_dsn, settings.POSTGRES_TIMEOUT_MS, channel_id
            )[0]
            if channel_config is None:
                logger.error(f"Channel '{channel_id}' not found in config.")
                raise Exception(f"Channel '{channel_id}' not found in config table.")
            total_distrib_amt = sum([d['amount'] for d in distributions])
            tax_pct = channel_config['token_tax_pct']
            tax_amount = int(total_distrib_amt * tax_pct)
            logger.info(f"Total tax amount: {tax_amount}")
            scm_distribute(
                http_session=s,
                dist_id=dist_id,
                channel_id=channel_id,
                tax_amt=tax_amount,
                distributions=distributions,
            )
            logger.info(f"Distributed tokens for channel '{channel_id}'")
            channel_db_utils.update_distribution_status(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=upsert_timeout_ms,
                dist_id=dist_id,
                channel_id=channel_id,
                txn_hash=None,
                old_status=TokenDistStatus.NULL,
                new_status=TokenDistStatus.SUBMITTED
            )

def scm_distribute(http_session, dist_id, channel_id, tax_amt, distributions):
    logger.info(
        f"call smartcontractmgr for distributionId: {dist_id} for channelId: '{channel_id}' with taxAmount: {tax_amt}"
    )
    logger.info(f"sample of distributions: {random.sample(distributions, min(10, len(distributions)))}")
    payload = {'distributionId': dist_id, 'taxAmount': str(tax_amt), 'channelId': channel_id, 'distributions': distributions}
    logger.trace(f"payload: {payload}")
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
        raise e 
        

def verify_distribution():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    upsert_timeout_ms = 120_000
    submitted_dist_ids_list = channel_db_utils.fetch_distribution_ids(
        logger, pg_dsn, settings.POSTGRES_TIMEOUT_MS, TokenDistStatus.SUBMITTED
    )
    logger.info(f"Channel distribution ids to be verified: {submitted_dist_ids_list}")
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
        timeout=(connect_timeout_s, read_timeout_s)
        for channel_id, dist_id in submitted_dist_ids_list:
            url = urllib.parse.urljoin(
                settings.CURA_SCMGR_URL, f"/distribution/{dist_id}",
            )
            logger.info(f"Checking token distribution status: {url}")
            try:
                response = s.get(
                    url, 
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    timeout=timeout
                )
                logger.info(f"{response.status_code}: {response.reason}")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Token distribution status: {data}")
                    channel_db_utils.update_distribution_status(
                        logger=logger,
                        pg_dsn=pg_dsn,
                        timeout_ms=upsert_timeout_ms,
                        dist_id=dist_id,
                        channel_id=channel_id,
                        txn_hash=data.get('tx'),
                        old_status=TokenDistStatus.SUBMITTED,
                        new_status=TokenDistStatus.SUCCESS,
                    )
                    channel_db_utils.update_token_bal(
                        logger=logger,
                        pg_dsn=pg_dsn,
                        timeout_ms=upsert_timeout_ms,
                        dist_id=dist_id,
                        channel_id=channel_id,
                    )                
                elif response.status_code == 404:
                    logger.warning(f"404 Error: Skipping channel {channel_id} :{response.reason}")
                    continue
            except Exception as e:
                logger.error(f"Failed to call smartcontractmgr: {e}")
                raise e
            logger.info(f"Prepping distribution for channel '{channel_id}'")


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

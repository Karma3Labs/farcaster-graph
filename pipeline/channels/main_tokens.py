# standard dependencies
import sys
import argparse
from enum import Enum
import urllib.parse
from urllib3.util import Retry
import random

# local dependencies
from config import settings, Database
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
  weekly = 'weekly'

class Task(Enum):
  prep = 'prep'
  distrib = 'distrib'
  verify = 'verify'

def prepare_for_distribution(database: Database, scope: Scope, reason: str):
    match database:
        case Database.EIGEN2:
            pg_dsn = settings.POSTGRES_DSN.get_secret_value()
        case Database.EIGEN8:
            pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
        case _:
            raise ValueError(f"Unknown database: {database}")
    insert_timeout_ms = 120_000
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
            token_live_in_db = channel['is_tokens']
            if scope == Scope.weekly and not token_live_in_db:
                logger.info(f"Channel '{channel_id}' scope: {scope}, token_live_in_db: {token_live_in_db}")
                logger.warning(f"Skipping distribution for channel '{channel_id}'")
                continue
            is_new_airdrop = False
            if not token_live_in_db:
                # In Postgres, we don't know if channel token is launched;
                # ...let's query Cura Smart Contract Manager to see if we need to do an airdrop
                try:
                    path = f"/token/lookupTokenForChannel/{channel_id}"
                    logger.info(f"GET {path}")
                    response = s.get(
                        urllib.parse.urljoin(settings.CURA_SCMGR_URL,path),
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                        timeout=(connect_timeout_s, read_timeout_s),
                    )
                    if response.status_code == 200:
                        channel_token = response.json()
                        token_address = channel_token.get('tokenAddress')      
                        claim_contract_address = channel_token.get('claimContractAddress')                  
                        if token_address and claim_contract_address:
                            logger.info(f"Channel '{channel_id}' has token {channel_token}.")
                            token_metadata = channel_token.get('tokenMetadata')
                            if token_metadata:
                                symbol = token_metadata.get('symbol')
                                total_supply = int(token_metadata.get('supply') / 1e18) if channel_token.get('supply') else 1_000_000_000 # 1 billion * 1e18
                                creator_cut = int(token_metadata.get('creatorCut')) if token_metadata.get('creatorCut') else 500 # 500 = 50%
                                vesting_months = int(token_metadata.get('vestingPeriod')) if token_metadata.get('vestingPeriod') else 36 # 36 months
                                airdrop_pmil = int(token_metadata.get('airdropPermil')) if token_metadata.get('airdropPermil') else 50 #  50 = 5%
                                community_supply = int(total_supply * creator_cut /  (10 * 100))
                                token_airdrop_budget = int(community_supply * airdrop_pmil / (10 * 100))
                                token_daily_budget = int((community_supply - token_airdrop_budget) / ((vesting_months/12) * 52 * 7))
                                logger.info(
                                    f"Channel '{channel_id}'"
                                    f" symbol: {symbol}"
                                    f", total supply: {total_supply}"
                                    f", creator cut: {creator_cut}"
                                    f", vesting months: {vesting_months}"
                                    f", airdrop pmil: {airdrop_pmil}"
                                    f", community supply: {community_supply}"
                                    f", token airdrop budget: {token_airdrop_budget}"
                                    f", token daily budget: {token_daily_budget}"
                                )
                                channel_db_utils.update_channel_rewards_config(
                                    logger=logger,
                                    pg_dsn=pg_dsn,
                                    timeout_ms=insert_timeout_ms,
                                    channel_id=channel_id,
                                    symbol=symbol,
                                    total_supply=total_supply,
                                    creator_cut=creator_cut,
                                    vesting_months=vesting_months,
                                    airdrop_pmil=airdrop_pmil,
                                    community_supply=community_supply,
                                    token_airdrop_budget=token_airdrop_budget,
                                    token_daily_budget=token_daily_budget
                                )
                            # this channel token is launched by SCM but we didn't see it in Postgres
                            # ...therefore conclude that this is token launch
                            # ...therefore conclude airdrop
                            is_new_airdrop = True
                            reason = "airdrop"
                        else:
                            logger.info(f"Channel '{channel_id}' token not fully launched: {channel_token}.")
                    elif response.status_code == 404:
                        logger.warning(f"404 Error: Skipping channel {channel_id} :{response.reason}")
                        continue
                except Exception as e:
                    logger.error(f"Failed to call smartcontractmgr: {e}")
                    raise e
            logger.info(
                f"Channel '{channel_id}' scope: {scope}"
                f", is_new_airdrop: {is_new_airdrop}, token_live_in_db: {token_live_in_db}"
            )
            if (scope == Scope.weekly and token_live_in_db) or (scope == Scope.airdrop and is_new_airdrop):
                # Token was already live in db and we are doing weekly distributions
                # ...or token was just launched and we are doing airdrop
                # ...let's prepare for distributing tokens.
                logger.info(f"Prepping distribution for channel '{channel_id}'")
                dist_id = channel_db_utils.insert_tokens_log(
                    logger=logger,
                    pg_dsn=pg_dsn,
                    timeout_ms=insert_timeout_ms,
                    channel_id=channel_id,
                    reason=reason,
                    is_airdrop=is_new_airdrop,
                    batch_size=settings.CURA_SCMGR_BATCH_SIZE
                )
                logger.info(f"Prepped distribution for channel '{channel_id}': {dist_id}")
            else:
                logger.info(f"Skipping distribution for channel '{channel_id}'")


def distribute_tokens():
    # logger.error("Short-circuiting token distribution.")
    # return
    if settings.IS_TEST:
        logger.warning("Test mode: skipping token distribution.")
        return
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
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
            batch_id = channel_distributions[2]
            distributions = channel_distributions[3]
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
            logger.info(f"Distributing tokens for channel '{channel_id}'")
            scm_distribute(
                http_session=s,
                dist_id=dist_id,
                batch_id=batch_id,
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
                batch_id=batch_id,
                channel_id=channel_id,
                txn_hash=None,
                old_status=TokenDistStatus.NULL,
                new_status=TokenDistStatus.SUBMITTED
            )


def scm_distributionId(dist_id, batch_id):
    return f"{dist_id}-{batch_id}"

def scm_distribute(http_session, dist_id, batch_id, channel_id, tax_amt, distributions):
    # logger.error("Short-circuiting token distribution.")
    # return
    did = scm_distributionId(dist_id, batch_id)
    logger.info(
        f"call smartcontractmgr for distributionId: {did} for channelId: '{channel_id}' with taxAmount: {tax_amt}"
    )
    logger.info(f"sample of distributions: {random.sample(distributions, min(10, len(distributions)))}")
    payload = {'distributionId': did, 'taxAmount': str(tax_amt), 'channelId': channel_id, 'distributions': distributions}
    logger.trace(f"payload: {payload}")
    connect_timeout_s = settings.CURA_SCMGR_CONNECT_TIMEOUT_SECS
    read_timeout_s = settings.CURA_SCMGR_READ_TIMEOUT_SECS
    try:
        response = http_session.post(
            urllib.parse.urljoin(settings.CURA_SCMGR_URL,"/distribution/"),
            json=payload,
            timeout=(connect_timeout_s, read_timeout_s)
        )
        if response.status_code == 500:
            err_json = response.json()
            logger.error(f"500 Error: {response.json()}")
            if err_json.get('error') == 'Distribution already has an onchain transaction':
                logger.info(f"Distribution {did} already has an onchain transaction")
                return
            else:
                raise Exception(f"500 Error: {err_json}")
        elif response.status_code == 200:
            logger.info(f"200 OK: {response.json()}")
            return
        else:
            logger.error(f"Unexpected status code: {response.status_code}: {response.text}")
            raise Exception(f"Unexpected status code: {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to call smartcontractmgr: {e}")
        raise e 
        

def verify_distribution():
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
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
        for channel_id, dist_id, batch_id in submitted_dist_ids_list:
            url = urllib.parse.urljoin(
                settings.CURA_SCMGR_URL, f"/distribution/{scm_distributionId(dist_id, batch_id)}",
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
                        batch_id=batch_id,
                        channel_id=channel_id,
                        txn_hash=data.get('tx'),
                        old_status=TokenDistStatus.SUBMITTED,
                        new_status=TokenDistStatus.SUCCESS,
                    )
                    if settings.IS_TEST:
                        logger.warning(f"Skipping update_token_bal for channel {channel_id} in test mode")
                    else:
                        channel_db_utils.update_token_bal(
                            logger=logger,
                            pg_dsn=pg_dsn,
                            timeout_ms=upsert_timeout_ms,
                            dist_id=dist_id,
                            batch_id=batch_id,
                            channel_id=channel_id,
                        )                
                elif response.status_code == 404:
                    logger.warning(f"404 Error: Skipping channel {channel_id} :{response.reason}")
                    continue
            except Exception as e:
                logger.error(f"Failed to call smartcontractmgr: {e}")
                raise e
            logger.info(f"Distribution verified for channel '{channel_id}'")


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
        help="airdrop or weekly",
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
    parser.add_argument(
        "-p",
        "--postgres",
        choices=list(Database),
        default=Database.EIGEN2,
        type=Database,
        help="eigen2 or eigen8",
        required=False,
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.task == Task.prep:
        logger.info('hello prepare')
        if not hasattr(args, "scope") or not hasattr(args, "reason"):
            logger.error("Scope and reason are required for preparing distribution.")
            sys.exit(1)
        prepare_for_distribution(args.postgres, args.scope, args.reason)
    elif args.task == Task.distrib:
        logger.info('hello distribute')
        distribute_tokens()
    elif args.task == Task.verify:
        logger.info('hello verify')
        verify_distribution()
    else:
        raise Exception(f"Unknown task {args.task}")

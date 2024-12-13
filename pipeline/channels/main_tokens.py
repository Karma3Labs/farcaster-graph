# standard dependencies
import sys
import argparse
from enum import Enum

# local dependencies
from config import settings
from . import channel_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import niquests

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

def prepare_for_distribution(scope: Scope):
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = 180_000
    is_airdrop = True if scope == Scope.airdrop else False
    channel_db_utils.insert_tokens_log(logger, pg_dsn, sql_timeout_ms, is_airdrop)

def distribute_tokens():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    sql_timeout_ms = settings.POSTGRES_TIMEOUT_SECS * 1000
    while True:
        # todo maybe? - parallelize this ? dbpool, http pool ?
        channel_distributions = channel_db_utils.fetch_one_channel_distributions(
            logger=logger,
            pg_dsn=pg_dsn,
            timeout_ms=sql_timeout_ms,
        )
        if channel_distributions is None:
            logger.info("No more channels to distribute.")
            break
        channel_id = channel_distributions[0]
        distributions = channel_distributions[1]
        call_smartcontractmgr(channel_id, distributions)
        logger.info(f"Distributed tokens for channel '{channel_id}'")
        # WARNING: big assumption that no new inserts have happened in the meanwhile
        # ... todo maybe? - move to a select for update  2-phase commit model
        channel_db_utils.update_distribution_status(
            logger=logger,
            pg_dsn=pg_dsn,
            timeout_ms=sql_timeout_ms,
            channel_id=channel_id,
        )

def call_smartcontractmgr(channel_id, distributions):
    logger.info(
        f"call smartcontractmgr for channel '{channel_id}'"
        f" with distributions {distributions}"
    )
    headers = {'API-Key': settings.CURA_SCMGR_API_KEY.get_secret_value()}
    # TODO generate req_id or distribution_id
    payload = {'channel_id': channel_id, 'distributions': distributions}
    logger.info(f"payload: {payload}")
    try:
        response = niquests.post(settings.CURA_SCMGR_URL, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to call smartcontractmgr: {e}")
        raise e 

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
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    if args.task == Task.prep:
        logger.info('hello prepare')
        if not hasattr(args, "scope"):
            logger.error("Scope is required for preparing distriubution.")
            sys.exit(1)
        prepare_for_distribution(args.scope)
    elif args.task == Task.distrib:
        logger.info('hello distribute')
        distribute_tokens()
    elif args.task == Task.verify:
        logger.info('hello verify')
        verify_distribution()
    else:
        raise Exception(f"Unknown task {args.task}")

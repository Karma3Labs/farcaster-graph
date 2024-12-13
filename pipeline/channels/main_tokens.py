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
    pass

def verify_distribution():
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

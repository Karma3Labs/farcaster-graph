# standard dependencies
import argparse
import sys
from datetime import datetime
from enum import StrEnum

import numpy as np
import pandas as pd

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

import db_utils
import utils

# local dependencies
from config import Database, settings

from . import channel_db_utils

# enable copy-on-write in prep for pandas 3.0
pd.set_option("mode.copy_on_write", True)

# Configure logger
logger.remove()
level_per_module = {"": settings.LOG_LEVEL, "silentlib": False}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)

load_dotenv()


class Model(StrEnum):
    weighted = "weighted"
    reddit = "reddit"


class WeightedModel(StrEnum):
    # default = "default"
    # sqrt_weighted = "sqrt_weighted"
    cbrt_weighted = "cbrt_weighted"
    # logeps_weighted = "logeps_weighted"


class RedditModel(StrEnum):
    pass
    # reddit_default = "reddit_default"
    # reddit_cast_weighted = "reddit_cast_weighted"


class Task(StrEnum):
    genesis = "genesis"
    compute = "compute"
    update = "update"
    gapfill = "gapfill"


def main(database: Database, task: Task, target_date_str: str):
    allowlisted_only = True
    is_v1 = False
    match database:
        case Database.EIGEN2:
            pg_dsn = settings.POSTGRES_DSN.get_secret_value()
            pg_url = settings.POSTGRES_URL.get_secret_value()
        case Database.EIGEN8:
            allowlisted_only = False
            is_v1 = True
            pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
            pg_url = settings.ALT_POSTGRES_URL.get_secret_value()
        case _:
            raise ValueError(f"Unknown database: {database}")

    sql_timeout_ms = 120_000

    match task:
        case Task.genesis:
            logger.info("Points genesis distribution")
            channel_db_utils.insert_genesis_points(logger, pg_dsn, sql_timeout_ms)
        case Task.compute | Task.gapfill:
            logger.info("Computing 1 day distribution")

            ##### RedditModel has no models anymore. This code block is left for reference.
            # # Reddit-style Karma Points
            # for model in RedditModel:
            #     if model == RedditModel.reddit_cast_weighted:
            #         cast_wt = 2
            #     else:
            #         cast_wt = 0
            #     channel_db_utils.insert_reddit_points_log(
            #         logger,
            #         pg_dsn,
            #         sql_timeout_ms,
            #         model_name=model.value,
            #         reply_wt=1,
            #         recast_wt=5,
            #         like_wt=1,
            #         cast_wt=cast_wt,
            #     )

            # Score Weighted Model
            if task == Task.gapfill:
                gapfill = True
                date_str = target_date_str
            else:
                gapfill = False
                date_str = None
            df = channel_db_utils.fetch_weighted_fid_scores_df(
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=sql_timeout_ms,
                reply_wt=1,
                recast_wt=5,
                like_wt=1,
                cast_wt=0,
                model_names=[e.value for e in WeightedModel],
                allowlisted_only=allowlisted_only,
                is_v1=is_v1,
                gapfill=gapfill,
                date_str=date_str,
            )
            logger.info(utils.df_info_to_string(df, with_sample=True, head=True))
            if len(df) == 0:
                logger.info("No points to distribute")
                return
            TOTAL_POINTS = 10_000
            PERCENTILE_CUTOFF = 0.1
            df["percent_rank"] = df.groupby("channel_id")["score"].rank(pct=True)
            df = df[df["percent_rank"] > PERCENTILE_CUTOFF]  # drop bottom 10%

            for model in WeightedModel:
                if model == WeightedModel.cbrt_weighted:
                    transformed = np.cbrt(df["score"])
                # elif model == WeightedModel.sqrt_weighted:
                #     transformed = np.sqrt(df['score'])
                # elif model == WeightedModel.default:
                #     transformed = df['score']
                # elif model == WeightedModel.logeps_weighted:
                #     epsilon = 1e-10
                #     transformed = np.log(df['score'] + epsilon)
                #     # Shift to make all values positive
                #     transformed = transformed - transformed.min() + epsilon
                # end if
                df["transformed"] = transformed
                df["weights"] = df.groupby("channel_id")["transformed"].transform(
                    lambda x: x / x.sum()
                )
                df["earnings"] = df["weights"] * TOTAL_POINTS
                df["earnings"] = df["earnings"].round(0).astype(int)
                final_df = df[["fid", "channel_id", "earnings"]]
                final_df["model_name"] = model.value
                if task == Task.gapfill:
                    final_df["notes"] = f"GAPFILL-{date_str}"
                logger.info(
                    utils.df_info_to_string(final_df, with_sample=True, head=True)
                )
                logger.info(f"Inserting data into the database for model {model.value}")
                try:
                    db_utils.df_insert_copy(
                        pg_url=pg_url,
                        df=final_df,
                        dest_tablename="k3l_channel_points_log",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to insert data into the database for model {model.value}: {e}"
                    )
                    raise e
        case Task.update:
            # uses the default weighted model to update points balances
            logger.info("Updating points balances with cbrt_weighted model")
            channel_db_utils.update_points_balance_v5(
                logger, pg_dsn, sql_timeout_ms, allowlisted_only
            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--task",
        choices=list(Task),
        type=Task,
        help="task to perform",
        required=True,
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
    parser.add_argument(
        "-g",
        "--gapfill-date",
        help="Date for gapfill, format: YYYY-MM-DD",
        required=False,
        type=str,
    )

    args = parser.parse_args()
    print(args)
    if args.task == Task.gapfill:
        if args.gapfill_date is None:
            raise ValueError("gapfill-date is required for gapfill")

        # if gapfill-date is not a valid date, the next line throws an error
        datetime.strptime(args.gapfill_date, "%Y-%m-%d")

    logger.info(settings)

    main(args.postgres, args.task, target_date_str=args.gapfill_date)

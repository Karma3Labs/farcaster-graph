import os
import sys
import time
from datetime import datetime

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from loguru import logger
from openrank_sdk import EigenTrust
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values

from config import settings

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


def load_localtrust_df_from_dune() -> pd.DataFrame:
    pd.set_option("display.float_format", "{:.6f}".format)
    dune = DuneClient(api_key=settings.DUNE_API_KEY)

    # pull localtrust values https://dune.com/queries/3955994
    # dune runs the query every 6 hours of UTC time.
    query_values = QueryBase(query_id=3955994)
    results_values = dune.get_latest_result(query_values)
    values_df = pd.DataFrame(data=results_values.get_rows())

    logger.info(
        "Loaded localtrust values from Dune. Number of rows: {}", len(values_df)
    )
    return values_df


def load_pretrust_df_from_localtrust(values_df: pd.DataFrame) -> pd.DataFrame:
    # Calculate total received amounts for each user (j)
    total_received_amount = values_df.groupby("j")["v"].sum()
    logger.info("Calculated total received amounts for each user.")

    # Calculate the sum of all received amounts
    total_received_sum = total_received_amount.sum()
    logger.info("Calculated the sum of all received amounts: {}", total_received_sum)

    # Define pretrust based on the proportion of received amounts
    pretrust_dict = {
        user: amount / total_received_sum
        for user, amount in total_received_amount.items()
    }

    # Convert pretrust dictionary to array of {"i": user, "v": amount}
    pretrust_a = [{"i": user, "v": amount} for user, amount in pretrust_dict.items()]

    pretrust_a_df = pd.DataFrame(pretrust_a)
    pretrust_a_df = pretrust_a_df.sort_values(by="v", ascending=False)
    logger.info("Created pretrust dataframe. Number of rows: {}", len(pretrust_a_df))
    return pretrust_a_df


def run_eigentrust(localtrust_df: pd.DataFrame, pretrust_df: pd.DataFrame):
    localtrust = [
        l for l in localtrust_df[["i", "j", "v"]].to_dict("records") if l["v"] > 0.0
    ]
    logger.info("Filtered localtrust dataframe. Number of records: {}", len(localtrust))

    pretrust = [p for p in pretrust_df[["i", "v"]].to_dict("records") if p["v"] > 0.0]
    pretrust_top_n = 100
    pretrust = pretrust[:pretrust_top_n]
    logger.info("Filtered pretrust dataframe to top {} entries.", pretrust_top_n)

    alpha = 0.1
    a = EigenTrust(
        host_url=settings.GO_EIGENTRUST_URL, alpha=alpha
    )  # higher alpha weights pretrust more

    logger.info("Running EigenTrust algorithm...")
    scores = a.run_eigentrust(localtrust, pretrust)
    logger.info("EigenTrust algorithm completed. Number of scores: {}", len(scores))

    return scores


def insert_scores_to_db(scores):
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()
    score_tuples = [(score["i"], score["v"]) for score in scores]

    conn = None
    try:
        # Connect to the database
        logger.info("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(pg_dsn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Start a transaction
        logger.info("Starting a transaction to update the table with new scores...")
        cur.execute("BEGIN;")

        # Create a temporary table
        temp_table_name = "degen_tip_temp"
        logger.info("Creating temporary table {}...", temp_table_name)
        cur.execute(
            f"""
        CREATE TEMP TABLE {temp_table_name} (
            i bigint PRIMARY KEY,
            v real
        ) ON COMMIT DROP;
        """
        )

        # Insert data into the temporary table
        logger.info("Inserting scores into the temporary table...")
        insert_query = f"""
        INSERT INTO {temp_table_name} (i, v)
        VALUES %s
        """
        execute_values(cur, insert_query, score_tuples)

        # Truncate the original table and insert data from the temporary table
        logger.info("Swapping data between temporary table and the existing table...")
        cur.execute(
            """
        TRUNCATE TABLE degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1;
        INSERT INTO degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 (i, v)
        SELECT i, v FROM degen_tip_temp;
        """
        )

        # Commit the transaction
        logger.info("Committing the transaction...")
        cur.execute("COMMIT;")
        logger.info("Scores inserted and table updated successfully.")
    except (Exception, psycopg2.Error) as error:
        logger.error("Error while connecting to PostgreSQL: {}", error)
        if conn:
            conn.rollback()
            logger.warning("Transaction rolled back due to error.")
        raise error
    finally:
        if conn:
            cur.close()
            conn.close()
            logger.info("PostgreSQL connection is closed")


def update_degen_tip_table():
    logger.info("Starting update of degen tip table...")
    localtrust_df = load_localtrust_df_from_dune()
    pretrust_df = load_pretrust_df_from_localtrust(localtrust_df)
    scores = run_eigentrust(localtrust_df, pretrust_df)
    insert_scores_to_db(scores)
    logger.info("Update of degen tip table completed.")


if __name__ == "__main__":
    update_degen_tip_table()

import os
import sys
import time
from datetime import datetime

import psycopg2
from dotenv import load_dotenv
from loguru import logger
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


def update_degen_tips():
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()

    conn = None
    try:
        # Connect to the database
        logger.info("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(pg_dsn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Create a cursor
        cur = conn.cursor()

        # Begin a transaction
        logger.info("Starting a new transaction...")
        cur.execute("BEGIN;")

        # Get the last processed timestamp
        logger.info("Fetching the last processed timestamp...")
        cur.execute(
            """
        SELECT
            COALESCE(MAX(parsed_at), CURRENT_TIMESTAMP) as parsed_at,
            max(timestamp) as last_cast_timestamp
        FROM k3l_degen_tips;
        """
        )
        result = cur.fetchone()
        if result and result[0]:
            last_parsed_at = result[0]
        else:
            last_parsed_at = datetime.now()

        if result and result[1]:
            last_processed_ts = result[1]
        else:
            raise ValueError("No last processed timestamp found in the database.")

        last_parsed_at_int = int(time.mktime(last_parsed_at.timetuple()))
        last_processed_ts_int = int(time.mktime(last_processed_ts.timetuple()))
        logger.info(
            f"Last parsed timestamp: {last_parsed_at} (Unix: {last_parsed_at_int})"
        )
        logger.info(
            f"Last cast timestamp: {last_processed_ts} (Unix: {last_processed_ts_int})"
        )

        # Convert the timestamp to a string for logging purposes
        last_processed_ts_str = last_processed_ts.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Converted last_processed_ts to string: {last_processed_ts_str}")

        # Define the common table expressions (CTEs)
        logger.info("Executing the main query with CTEs to fetch DEGEN tips data...")
        query = f"""
        WITH deduct_degen AS (
            SELECT
                casts.parent_hash AS cast_hash
            FROM
                casts
            WHERE
                UPPER(casts.text) LIKE '%DEDEGEN%'
                AND casts.fid = ANY(ARRAY[2904, 15983, 12493, 250874, 307834, 403619, 269694, 234616, 4482, 274, 243818, 385955, 210201, 3642, 539, 294226, 16405, 3827, 320215, 7637, 4027, 9135, 7258, 211186, 10174, 7464, 13505, 11299, 1048, 2341, 617, 191503, 4877, 3103, 12990, 390940, 7237, 5034, 195117, 8447, 20147, 262938, 307739, 17064, 351897, 426045, 326433, 273147, 270504, 419741, 446697, 354795])
                AND casts.deleted_at IS NULL
                AND casts."timestamp" > '{last_processed_ts_str}'
            GROUP BY
                casts.parent_hash
            HAVING COUNT(*) >= 5
        ),
        nuke_degen AS (
            SELECT
                casts.parent_hash AS cast_hash
            FROM
                casts
            WHERE
                UPPER(casts.text) LIKE '%DEDEGEN%'
                AND casts.fid IN (2904, 15983, 12493)
                AND casts.deleted_at IS NULL
                AND casts."timestamp" > '{last_processed_ts_str}'
            GROUP BY
                casts.parent_hash
        ),
        parsed_casts AS (
            SELECT
                casts.*,
                COALESCE(regexp_match[1], '0')::NUMERIC AS degen_amount,
                (regexp_match IS NOT NULL) AS is_valid
            FROM
                casts
            LEFT JOIN LATERAL (
                SELECT regexp_matches(casts.text, '(\\d+(?:\\.\\d+)?)\\s*\\$DEGEN') AS regexp_match
            ) AS regexp_matches ON TRUE
            WHERE
                casts."timestamp" > '{last_processed_ts_str}'
        )
        SELECT
            parsed_casts.hash,
            parsed_casts.parent_hash,
            parsed_casts.fid,
            parsed_casts.parent_fid,
            parsed_casts.degen_amount,
            parsed_casts."timestamp",
            parent_casts."timestamp",
            CURRENT_TIMESTAMP
        FROM
            parsed_casts
        INNER JOIN
            casts AS parent_casts ON parsed_casts.parent_hash = parent_casts.hash
        WHERE
            parsed_casts.is_valid
            AND parsed_casts.parent_hash IS NOT NULL
            AND parsed_casts.parent_fid <> parsed_casts.fid
            AND parsed_casts.deleted_at IS NULL
            AND parsed_casts.fid NOT IN (217745, 234434, 244128, 364927)
            AND parsed_casts.parent_fid NOT IN (364927)
            AND COALESCE(ARRAY_POSITION(parsed_casts.mentions, 364927), 0) = 0
            AND NOT EXISTS (
                SELECT 1
                FROM k3l_degen_tips
                WHERE k3l_degen_tips.cast_hash = parsed_casts.hash
            )
            AND NOT EXISTS (
                SELECT 1
                FROM deduct_degen
                WHERE deduct_degen.cast_hash = parsed_casts.parent_hash
            )
            AND NOT EXISTS (
                SELECT 1
                FROM nuke_degen
                WHERE nuke_degen.cast_hash = parsed_casts.parent_hash
            )
        ORDER BY parsed_casts."timestamp" DESC
        """

        cur.execute(query)
        degen_tips_data = cur.fetchall()

        # Prepare data for insertion using execute_values
        insert_query = """
        INSERT INTO k3l_degen_tips (cast_hash, parent_hash, fid, parent_fid, degen_amount, "timestamp", parent_timestamp, parsed_at)
        VALUES %s
        ON CONFLICT (cast_hash) DO NOTHING
        """
        execute_values(cur, insert_query, degen_tips_data)

        # Fetch the number of rows inserted
        rows_inserted = cur.rowcount
        logger.info(f"Inserted {rows_inserted} new eligible DEGEN tips.")

        # Commit the transaction
        cur.execute("COMMIT;")
        logger.info("Transaction committed successfully.")

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


if __name__ == "__main__":
    update_degen_tips()

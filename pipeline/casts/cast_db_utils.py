from io import StringIO
import logging

import requests

from timer import Timer
import time
from config import settings
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import pandas as pd

def fetch_rows_df(*args, logger: logging.Logger, sql_query: str, pg_dsn: str):
    start_time = time.perf_counter()
    if settings.IS_TEST:
      sql_query = f"{sql_query} LIMIT 10"
    logger.info(f"Execute query: {sql_query}")
    with psycopg2.connect(
        pg_dsn,
        connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, *args)
            rows = cursor.fetchall()
            cols = list(map(lambda x: x[0], cursor.description))
            df = pd.DataFrame(rows, columns=cols)
    logger.info(f"db took {time.perf_counter() - start_time} secs for {len(rows)} rows")
    return df


@Timer(name="insert_cast_action")
def insert_cast_action(
    logger: logging.Logger, pg_dsn: str, insert_limit: int, is_v1: bool = False
):
    # TODO different max_at for casts and replies, and different for likes and recasts
    tbl_name = f"k3l_cast_action{'_v1' if is_v1 else ''}"
    insert_sql = f"""
        INSERT INTO {tbl_name}
            (channel_id, fid, cast_hash, casted, replied, recasted, liked, action_ts, created_at)
        WITH max_cast_action AS (
            SELECT
            coalesce(max(created_at), now() - interval '5 days')  as max_at
            FROM {tbl_name}
        )
        SELECT
            ch.id as channel_id,
            casts.fid as fid,
            casts.hash as cast_hash,
            1 as casted,
            0 as replied,
            0 as recasted,
            0 as liked,
            casts.timestamp as action_ts,
            casts.created_at
        FROM casts CROSS JOIN max_cast_action
        LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
        WHERE
            (casts.timestamp > now() - interval '5 days' AND casts.timestamp <= now())
            AND
            (casts.created_at
            BETWEEN max_cast_action.max_at
            AND now())
            AND casts.deleted_at IS NULL
        UNION ALL
        SELECT
            ch.id as channel_id,
            casts.fid as fid,
            casts.parent_hash as cast_hash,
            0 as casted,
            1 as replied,
            0 as recasted,
            0 as liked,
            casts.timestamp as action_ts,
            casts.created_at
        FROM casts CROSS JOIN max_cast_action
        LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
        WHERE
            (casts.timestamp > now() - interval '5 days' AND casts.timestamp <= now())
            AND
            casts.parent_hash IS NOT NULL
            AND
            casts.created_at
            BETWEEN max_cast_action.max_at
                AND now()
            AND casts.deleted_at IS NULL
        UNION ALL
        SELECT
            ch.id as channel_id,
            reactions.fid as fid,
            reactions.target_hash as cast_hash,
            0 as casted,
            0 as replied,
            CASE reactions.reaction_type WHEN 2 THEN 1 ELSE 0 END as recasted,
            CASE reactions.reaction_type WHEN 1 THEN 1 ELSE 0 END as liked,
            reactions.timestamp as action_ts,
            reactions.created_at
        FROM reactions CROSS JOIN max_cast_action
        INNER JOIN casts as casts on (casts.hash = reactions.target_hash)
        LEFT JOIN warpcast_channels_data as ch on (ch.url = casts.root_parent_url)
        WHERE
            (casts.timestamp > now() - interval '5 days' AND casts.timestamp <= now())
            AND
            reactions.created_at
            BETWEEN max_cast_action.max_at
                AND now()
            AND
            reactions.reaction_type IN (1,2)
            AND
            reactions.target_hash IS NOT NULL
            AND reactions.deleted_at IS NULL
        ORDER BY created_at ASC
        LIMIT {insert_limit}
        ON CONFLICT(cast_hash, fid, action_ts)
        DO NOTHING -- expect duplicates because of between clause
    """
    with psycopg2.connect(
    pg_dsn,
    connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {insert_sql}")
            cursor.execute(insert_sql)
            rows = cursor.rowcount
            logger.info(f"Inserted {rows} rows into {tbl_name}")

@Timer(name="backfill_cast_action")
def backfill_cast_action(
    logger: logging.Logger,
    pg_dsn: str,
    insert_limit: int,
    target_month: datetime,
    is_v1: bool = False,
) -> int:
    """
    This function performs backfilling of cast actions for a specified month.
    Parameters:
    - logger (logging.Logger): The logger for logging information.
    - pg_dsn (str): The PostgreSQL data source name for connection.
    - insert_limit (int): The maximum number of rows to insert.
    - target_month (datetime): The month for which to backfill data.
    - is_v1 (bool, optional): A flag indicating versioning. Defaults to False.

    Returns:
    - int: The number of rows inserted.

    The function starts from the end of the month and works backwards
    inserting cast actions into the database.
    It handles both primary and parent cast actions,
    ensuring no duplicates are inserted due to the constraints.
    """
    # Example:
    # program args: 2024-11
    # target_month = datetime(2024, 11, 1, 0, 0, 0)
    # start_at = datetime(2024, 10, 31, 23, 59, 59)
    # target_month_str = "2024-11-01 00:00:00"
    # partition_name = "k3l_cast_action_v1_y2024m11"
    # first time invocation:
    # # min_ts = null or "2024-11-30 23:59:59"
    # # cutoff_ts = "2024-11-01 00:00:00"
    # eligible actions are: between min_ts and cutoff_ts ordered by ts desc
    # second time invocation:
    # # min_ts = "2024-11-28 18:29:05"
    # # cutoff_ts = "2024-11-01 00:00:00"
    # eligible actions are: between min_ts and cutoff_ts ordered by ts desc

    start_at = target_month - timedelta(seconds=1)
    start_at_str = start_at.strftime("%Y-%m-%d %H:%M:%S")
    target_month_str = target_month.strftime("%Y-%m-%d %H:%M:%S")
    partition_name = f"k3l_cast_action_{'v1_' if is_v1 else ''}{target_month.strftime('y%Ym%m')}"

    logger.info(f"backfilling {partition_name} from {start_at_str} to {target_month_str}")

    insert_sql = f"""
    INSERT INTO {partition_name}
        (channel_id, fid, cast_hash, casted, replied, recasted, liked, action_ts, created_at)
    WITH
      min_cast_action AS (
        SELECT
          COALESCE(min(action_ts), '{start_at_str}'::timestamp + interval '1 month') as min_ts, 
          '{target_month_str}'::timestamp as cutoff_ts
        FROM {partition_name}
      )
    SELECT
      ch.id as channel_id,
      casts.fid as fid,
      casts.hash as cast_hash,
      1 as casted,
      0 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts CROSS JOIN min_cast_action
    LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
    WHERE
      casts.timestamp >= min_cast_action.cutoff_ts
      AND
      casts.timestamp
        BETWEEN min_cast_action.min_ts - interval '12 hours'
                AND min_cast_action.min_ts
      AND casts.deleted_at IS NULL
    UNION ALL
    SELECT
      ch.id as channel_id,
      casts.fid as fid,
      casts.parent_hash as cast_hash,
      0 as casted,
      1 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts CROSS JOIN min_cast_action
    LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
    WHERE
      casts.timestamp >= min_cast_action.cutoff_ts
      AND
      casts.parent_hash IS NOT NULL
      AND
      casts.timestamp
        BETWEEN min_cast_action.min_ts - interval '12 hours'
                AND min_cast_action.min_ts
      AND casts.deleted_at IS NULL
    UNION ALL
    SELECT
      ch.id as channel_id,
      reactions.fid as fid,
      reactions.target_hash as cast_hash,
      0 as casted,
      0 as replied,
      CASE reactions.reaction_type WHEN 2 THEN 1 ELSE 0 END as recasted,
      CASE reactions.reaction_type WHEN 1 THEN 1 ELSE 0 END as liked,
      reactions.timestamp as action_ts,
      reactions.created_at
    FROM reactions CROSS JOIN min_cast_action
    INNER JOIN casts as casts on (casts.hash = reactions.target_hash)
    LEFT JOIN warpcast_channels_data as ch on (ch.url = casts.root_parent_url)
    WHERE
      reactions.timestamp >= min_cast_action.cutoff_ts
      AND
      reactions.timestamp
        BETWEEN min_cast_action.min_ts - interval '12 hours'
                AND min_cast_action.min_ts
      AND
      reactions.reaction_type IN (1,2)
      AND
      reactions.target_hash IS NOT NULL
      AND reactions.deleted_at IS NULL
    ORDER BY action_ts DESC
    LIMIT {insert_limit}
    ON CONFLICT(cast_hash, fid, action_ts)
    DO NOTHING -- expect duplicates because of between clause
  """
    with psycopg2.connect(
        pg_dsn,
        connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {insert_sql}")
            cursor.execute(insert_sql)
            rows = cursor.rowcount
            logger.info(f"Backfilled {rows} rows into {partition_name}")
            return rows

@Timer(name="gapfill_cast_action")
def gapfill_cast_action(
    logger: logging.Logger, pg_dsn: str, insert_limit: int, target_date: datetime, is_v1: bool = False
) -> int:
    target_date_str = target_date.strftime("%Y-%m-%d %H:%M:%S")
    tbl_name = f"k3l_cast_action{'_v1' if is_v1 else ''}"
    insert_sql = f"""
    INSERT INTO {tbl_name}
        (channel_id, fid, cast_hash, casted, replied, recasted, liked, action_ts, created_at)
    WITH
      missing_casts AS (
        SELECT
          ch.id as channel_id,
          casts.fid as fid,
          casts.hash as cast_hash,
          1 as casted,
          0 as replied,
          0 as recasted,
          0 as liked,
          casts.timestamp as action_ts,
          casts.created_at
        FROM casts
        LEFT JOIN {tbl_name}
          AS ca ON (
            casts.hash = ca.cast_hash
          )
        LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
        WHERE casts.timestamp
          BETWEEN '{target_date_str}'::timestamp AND ('{target_date_str}'::timestamp + interval '1 day')
        AND casts.deleted_at IS NULL
        AND ca.cast_hash IS NULL
        LIMIT {insert_limit / 4}
      ),
      missing_replies AS (
        SELECT
          ch.id as channel_id,
          casts.fid as fid,
          casts.parent_hash as cast_hash,
          0 as casted,
          1 as replied,
          0 as recasted,
          0 as liked,
          casts.timestamp as action_ts,
          casts.created_at
        FROM casts
        LEFT JOIN {tbl_name}
          AS ca ON (
            casts.parent_hash = ca.cast_hash
          )
        LEFT JOIN warpcast_channels_data as ch ON (ch.url = casts.root_parent_url)
        WHERE
          casts.parent_hash IS NOT NULL
          AND casts.timestamp
            BETWEEN '{target_date_str}'::timestamp AND ('{target_date_str}'::timestamp + interval '1 day')
          AND casts.deleted_at IS NULL
          AND ca.cast_hash IS NULL
        LIMIT {insert_limit / 4}
      ),
      missing_reactions AS (
        SELECT
          ch.id as channel_id,
          reactions.fid as fid,
          reactions.target_hash as cast_hash,
          0 as casted,
          0 as replied,
          CASE reactions.reaction_type WHEN 2 THEN 1 ELSE 0 END as recasted,
          CASE reactions.reaction_type WHEN 1 THEN 1 ELSE 0 END as liked,
          reactions.timestamp as action_ts,
          reactions.created_at
        FROM reactions
        LEFT JOIN {tbl_name}
          AS ca ON (
            reactions.target_hash = ca.cast_hash
          )
        INNER JOIN casts on (casts.hash = reactions.target_hash)
        LEFT JOIN warpcast_channels_data as ch on (ch.url = casts.root_parent_url)
        WHERE
          reactions.reaction_type IN (1,2)
          AND reactions.target_hash IS NOT NULL
          AND reactions.timestamp
            BETWEEN '{target_date_str}'::timestamp AND ('{target_date_str}'::timestamp + interval '1 day')
          AND reactions.deleted_at IS NULL
          AND ca.cast_hash IS NULL
        LIMIT {insert_limit / 2}
      )
    SELECT * FROM missing_casts
    UNION ALL
    SELECT * FROM missing_replies
    UNION ALL
    SELECT * FROM missing_reactions
    ON CONFLICT(cast_hash, fid, action_ts)
    DO NOTHING -- expect duplicates because of between clause
  """
    with psycopg2.connect(
        pg_dsn,
        connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {insert_sql}")
            cursor.execute(insert_sql)
            rows = cursor.rowcount
            logger.info(f"Gapfilled {rows} rows into {tbl_name}")
            return rows


@Timer(name="fetch_top_casters_df")
def fetch_top_casters_df(logger: logging.Logger, pg_dsn: str, is_v1: bool = False):
    tbl_name = f"k3l_cast_action{'_v1' if is_v1 else ''}"
    sql = f"""
        with
            latest_global_rank as (
            SELECT profile_id as fid, rank, score from k3l_rank g where strategy_id=9
            AND date in (select max(date) from k3l_rank)
            ),
            new_fids AS (
            SELECT fid
            FROM fids
            WHERE registered_at::date BETWEEN (now() - interval '30 days') AND now()
            ORDER BY registered_at DESC
            ),
            fid_cast_scores as (
                SELECT
                    hash as cast_hash,
                    SUM(
                        (
                            (10 * fids.score * ci.casted)
                            + (1 * fids.score * ci.replied)
                            + (5 * fids.score * ci.recasted)
                            + (1 * fids.score * ci.liked)
                        )
                        *
                        power(
                            1-(1/(365*24)::numeric),
                            (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ci.action_ts)) / (60 * 60))::numeric
                        )
                    ) as cast_score,
                    MIN(ci.action_ts) as cast_ts
                FROM k3l_recent_parent_casts as casts
                INNER JOIN {tbl_name} as ci
                    ON (ci.cast_hash = casts.hash
                        AND ci.action_ts BETWEEN now() - interval '3 days'
                        AND now() - interval '10 minutes')
                INNER JOIN latest_global_rank as fids ON (fids.fid = ci.fid )
                WHERE casts.created_at BETWEEN (now() - interval '1 day') AND now()
                AND casts.fid IN (SELECT fid FROM new_fids)
                GROUP BY casts.hash, ci.fid
                ORDER BY cast_ts desc
                -- LIMIT 100000
            )
            , scores AS (
                SELECT
                    cast_hash,
                    sum(power(fid_cast_scores.cast_score,2)) as cast_score,
                    MIN(cast_ts) as cast_ts
                FROM fid_cast_scores
                GROUP BY cast_hash
            ),
        cast_details as (
        SELECT
            '0x' || encode(casts.hash, 'hex') as cast_hash,
            DATE_TRUNC('hour', casts.timestamp) as cast_hour,
            casts.text,
            casts.embeds,
            casts.mentions,
            casts.fid,
            casts.timestamp,
            cast_score,
            row_number() over(partition by DATE_TRUNC('hour', casts.timestamp) order by random()) as rn,
                    fids_global_rank.rank AS global_rank
        FROM k3l_recent_parent_casts as casts
        INNER JOIN scores on casts.hash = scores.cast_hash
        INNER JOIN latest_global_rank AS fids_global_rank ON casts.fid = fids_global_rank.fid  -- Joining to get the rank
        WHERE casts.timestamp BETWEEN CURRENT_TIMESTAMP - INTERVAL '1 day' AND CURRENT_TIMESTAMP
        ORDER BY cast_score DESC
        OFFSET 0
        )
        select cast_hash,fid as i, cast_score as v from cast_details
        WHERE fid not in (select fid from pretrust_v2)
        order by cast_score DESC
    """
    return fetch_rows_df(logger=logger, sql_query=sql, pg_dsn=pg_dsn)


@Timer(name="fetch_top_spammers_df")
def fetch_top_spammers_df(
    logger: logging.Logger, pg_dsn: str, start_date: datetime, end_date: datetime
):
  start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
  end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

  sql = f"""
    WITH all_casts AS (
      SELECT
        fc.*
      FROM casts fc
      WHERE created_at BETWEEN '{start_date_str}' AND '{end_date_str}'
    ),
    distinct_fids AS (
      SELECT DISTINCT fid
      FROM all_casts
    ),
    parent_casts AS (
      SELECT
        fid,
        COUNT(*) AS total_parent_casts
      FROM all_casts
      WHERE parent_hash IS NULL
      GROUP BY fid
    ),
    replies_with_parent_hash AS (
      SELECT
        fid,
        COUNT(*) AS total_replies_with_parent_hash
      FROM all_casts
      WHERE parent_hash IS NOT NULL
      GROUP BY fid
    ),
    filtered_data AS (
      SELECT
        i,
        v,
        date,
        strategy_id
      FROM globaltrust
      WHERE strategy_id = 3
        AND date in (select max(date) from globaltrust)
    ),
    global_ranked_data AS (
      SELECT
        i,
        v,
        ROW_NUMBER() OVER (ORDER BY v DESC) AS rank,
        COUNT(*) OVER () AS total_rows
      FROM filtered_data
    ),
    bottom_percentage_data AS (
      SELECT
        i,
        rank,
        total_rows,
        CASE
          WHEN rank > 0.9 * total_rows THEN '10%'
          WHEN rank > 0.8 * total_rows THEN '20%'
          WHEN rank > 0.7 * total_rows THEN '30%'
          WHEN rank > 0.6 * total_rows THEN '40%'
          WHEN rank > 0.5 * total_rows THEN '50%'
          WHEN rank > 0.4 * total_rows THEN '60%'
          WHEN rank > 0.3 * total_rows THEN '70%'
          WHEN rank > 0.2 * total_rows THEN '80%'
          WHEN rank > 0.1 * total_rows THEN '90%'
          WHEN rank > 0.05 * total_rows THEN '95%'
          -- Add more cases as needed
          ELSE 'Above 95%'
        END AS bottom_percentage
      FROM global_ranked_data
    )
    ,
    user_data_filtered AS (
      SELECT
        fid,
        value
      FROM user_data
      WHERE type = 2
    )
    -- Final output
    SELECT
      dfid.fid,
      ud.value AS display_name,
      --bpd.bottom_percentage as bottom_global_percentage,
      COALESCE(pc.total_parent_casts, 0) + COALESCE(rp.total_replies_with_parent_hash, 0) as total_outgoing,
      (COALESCE(pc.total_parent_casts, 0) + COALESCE(rp.total_replies_with_parent_hash, 0))/(r.v+1e10) as spammer_score,
      COALESCE(pc.total_parent_casts, 0) AS total_parent_casts,
      COALESCE(rp.total_replies_with_parent_hash, 0) AS total_replies_with_parent_hash,
      r.v AS global_openrank_score,
      r.rank AS global_rank,
      r.total_rows AS total_global_rank_rows
    FROM distinct_fids dfid
    LEFT JOIN parent_casts pc ON dfid.fid = pc.fid
    LEFT JOIN replies_with_parent_hash rp ON dfid.fid = rp.fid
    LEFT JOIN global_ranked_data r ON dfid.fid = r.i
    LEFT JOIN bottom_percentage_data bpd ON r.i = bpd.i
    LEFT JOIN user_data_filtered ud ON dfid.fid = ud.fid
    WHERE (bpd.bottom_percentage != 'Above 95%' OR bpd.bottom_percentage IS NULL)
    AND (COALESCE(pc.total_parent_casts, 0) + COALESCE(rp.total_replies_with_parent_hash, 0)) > 30
    ORDER BY spammer_score DESC
  """
  return fetch_rows_df(logger=logger, sql_query=sql, pg_dsn=pg_dsn)

def insert_dune_table(api_key, namespace, table_name, scores_df):
  headers = {
      "X-DUNE-API-KEY": api_key,
      "Content-Type": "text/csv"
  }

  url = f"https://api.dune.com/api/v1/table/{namespace}/{table_name}/clear"
  clear_resp = requests.request("POST", url, data="", headers=headers)
  print('clear_resp', clear_resp.status_code, clear_resp.text)

  csv_buffer = StringIO()
  scores_df.to_csv(csv_buffer, index=False)
  csv_buffer.seek(0)

  url = f'https://api.dune.com/api/v1/table/{namespace}/{table_name}/insert'

  insert_resp = requests.request("POST", url, data=csv_buffer.getvalue(), headers=headers)
  print('insert to dune resp', insert_resp.status_code, insert_resp.text)
  return insert_resp
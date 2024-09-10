import logging

from timer import Timer
import time
from config import settings

import psycopg2
import psycopg2.extras
from asyncpg.pool import Pool
import asyncpg

async def fetch_rows(
        *args,
        logger: logging.Logger,
        sql_query: str,
        pool: Pool
):
    start_time = time.perf_counter()
    logger.debug(f"Execute query: {sql_query}")
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                # Run the query passing the request argument.
                try:
                    rows = await connection.fetch(
                        sql_query,
                        *args,
                        timeout=settings.POSTGRES_TIMEOUT_SECS
                    )
                except Exception as e:
                    logger.error(f"Failed to execute query: {sql_query}")
                    logger.error(f"{e}")
                    return [{"Unknown error. Contact K3L team"}]
    logger.info(f"db took {time.perf_counter() - start_time} secs for {len(rows)} rows")
    return rows

@Timer(name="insert_cast_action")
def insert_cast_action(logger: logging.Logger, pg_dsn: str, insert_limit: int):
  insert_sql = f"""
    INSERT INTO k3l_cast_action
    WITH max_cast_action AS (
      SELECT
        coalesce(max(created_at), now() - interval '5 days')  as max_at
      FROM k3l_cast_action
    )
    SELECT
      casts.fid as fid,
      casts.hash as cast_hash,
      1 as casted,
      0 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts, max_cast_action
    WHERE
    	casts.timestamp > now() - interval '5 days'
      AND
      casts.created_at
        BETWEEN max_cast_action.max_at
        AND now()
    UNION ALL
    SELECT
      casts.fid as fid,
      casts.parent_hash as cast_hash,
      0 as casted,
      1 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts CROSS JOIN max_cast_action
    WHERE
    	casts.timestamp > now() - interval '5 days'
      AND
      casts.parent_hash IS NOT NULL
      AND
      casts.created_at
        BETWEEN max_cast_action.max_at
          AND now()
    UNION ALL
    SELECT
      reactions.fid as fid,
      reactions.target_hash as cast_hash,
      0 as casted,
      0 as replied,
      CASE reactions.reaction_type WHEN 2 THEN 1 ELSE 0 END as recasted,
      CASE reactions.reaction_type WHEN 1 THEN 1 ELSE 0 END as liked,
      reactions.timestamp as action_ts,
      reactions.created_at
    FROM reactions CROSS JOIN max_cast_action
    WHERE
    	reactions.timestamp > now() - interval '5 days'
      AND
      reactions.created_at
        BETWEEN max_cast_action.max_at
          AND now()
      AND
      reactions.reaction_type IN (1,2)
      AND
      reactions.target_hash IS NOT NULL
    ORDER BY created_at ASC
    LIMIT {insert_limit}
    ON CONFLICT(cast_hash, fid, action_ts)
    DO NOTHING -- expect duplicates because of between clause
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {insert_sql}")
      cursor.execute(insert_sql)

@Timer(name="fetch_top_casters")
async def fetch_top_casters(logger: logging.Logger, pg_dsn: str):
  pool = await asyncpg.create_pool(pg_dsn,
                                         min_size=1,
                                         max_size=5)
  sql = f"""
    with
        latest_global_rank as (
          SELECT profile_id as fid, rank, score from k3l_rank g where strategy_id=3
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
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts BETWEEN now() - interval '3 days'
                    AND now() - interval '10 minutes')
            INNER JOIN latest_global_rank as fids ON (fids.fid = ci.fid )
            WHERE casts.created_at BETWEEN (now() - interval '1 day') AND now()
            AND casts.fid IN (SELECT fid FROM new_fids)
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts desc
--             LIMIT 100000
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
    select fid as i, cast_score as v from cast_details
    WHERE fid not in (select fid from pretrust)
    order by cast_score DESC
  """
  return await fetch_rows(logger=logger, sql_query=sql, pool=pool)


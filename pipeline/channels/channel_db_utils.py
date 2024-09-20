import logging

from timer import Timer
import time
from config import settings
from datetime import datetime

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


@Timer(name="fetch_top_casters")
async def fetch_top_casters(logger: logging.Logger, pg_dsn: str, channel_id: str, url: str):
    pool = await asyncpg.create_pool(pg_dsn,
                                     min_size=1,
                                     max_size=5)
    sql = f"""
    with 
        latest_global_rank as (
                select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=3
                    and date in (select max(date) from k3l_rank)
                ),
        fid_cast_scores as (
                    SELECT
                        hash as cast_hash,
                        SUM(
                            (
        --                         (1 * fids.score * ci.casted)
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
                                    ci.fid,
                        MIN(ci.action_ts) as cast_ts
                    FROM k3l_recent_parent_casts as casts
                    INNER JOIN k3l_cast_action as ci
                        ON (ci.cast_hash = casts.hash
                            AND ci.action_ts BETWEEN (CURRENT_TIMESTAMP - INTERVAL '1 day') AND (CURRENT_TIMESTAMP - INTERVAL '10 minutes')
                            AND casts.root_parent_url = '{url}')
                    INNER JOIN k3l_channel_rank as fids ON (fids.channel_id='{channel_id}' AND fids.fid = ci.fid )
                    LEFT JOIN automod_data as md ON (md.channel_id='{channel_id}' AND md.affected_userid=ci.fid AND md.action='ban')
                    WHERE casts.created_at BETWEEN CURRENT_TIMESTAMP - INTERVAL '1 day' AND CURRENT_TIMESTAMP
                            GROUP BY casts.hash, ci.fid
                    ORDER BY cast_ts DESC
                )
                , scores AS (
                    SELECT
                        cast_hash,
                            sum(power(fid_cast_scores.cast_score,2)) as cast_score,
                        MIN(cast_ts) as cast_ts,
                            COUNT (*) - 1 as reaction_count
                    FROM fid_cast_scores
                    GROUP BY cast_hash
                ),
                cast_details AS (
            SELECT
                '0x' || encode(scores.cast_hash, 'hex') as cast_hash,
                DATE_TRUNC('hour', scores.cast_ts) AS cast_hour,
                scores.cast_ts,
                scores.cast_score,
                scores.reaction_count as reaction_count,
                ci.text,
                ci.fid,
                fids.rank AS channel_rank,
                latest_global_rank.global_rank
            FROM scores
            INNER JOIN k3l_recent_parent_casts AS ci ON ci.hash = scores.cast_hash
            INNER JOIN latest_global_rank ON ci.fid = latest_global_rank.fid
            INNER JOIN k3l_channel_rank AS fids ON ci.fid = fids.fid AND fids.channel_id = 'parenting'
                WHERE ci.timestamp BETWEEN CURRENT_TIMESTAMP - INTERVAL '1 day' AND CURRENT_TIMESTAMP
            ORDER BY scores.cast_score DESC
            OFFSET 0
        )
        SELECT
            cast_hash,
            fid,
            cast_score,
                reaction_count,
            global_rank,
            channel_rank,
            cast_hour,
            cast_ts,
            text
        FROM cast_details
        ORDER BY cast_score DESC;
        """
    return await fetch_rows(logger=logger, sql_query=sql, pool=pool)

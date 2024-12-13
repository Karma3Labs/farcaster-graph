import logging

from timer import Timer
import time
from config import settings
from asyncpg.pool import Pool
import asyncpg
import psycopg2


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


def fetch_channel_casters(logger: logging.Logger, pg_dsn: str, channel_url: str) -> list[int]:
    query_sql = f"""
    SELECT
      DISTINCT(fid)
    FROM casts
    WHERE root_parent_url = '{channel_url}'
    """
    if settings.IS_TEST:
        query_sql = f"{query_sql} LIMIT 10"
    logger.debug(f"{query_sql}")
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query_sql)
            records = cursor.fetchall()
            fids = [row[0] for row in records]
            return fids

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

@Timer(name="update_points_balance_v1")
def update_points_balance_v1(logger: logging.Logger, pg_dsn: str, timeout_ms: int):
    # WARNING - EXTREME CAUTION - be very careful with these variables
    OLD_TBL = "k3l_channel_points_bal_old"
    LIVE_TBL = "k3l_channel_points_bal"
    NEW_TBL = "k3l_channel_points_bal_new"
    STRATEGY = "1d_engagement"
    NUM_NTILES = 10
    CUTOFF_NTILE = 9
    TOTAL_POINTS = 10_000
    ALLOC_INTERVAL = '22 hours'
    # WARNING - EXTREME CAUTION

    create_sql = (
        f"DROP TABLE IF EXISTS {OLD_TBL};"
        f"CREATE TABLE {NEW_TBL} (LIKE {LIVE_TBL} INCLUDING ALL);"
    )

    replace_sql = (
        f"ALTER TABLE {LIVE_TBL} RENAME TO {OLD_TBL};"
        f"ALTER TABLE {NEW_TBL} RENAME TO {LIVE_TBL};"
    )

    insert_sql = f"""
        WITH points_budget AS 
        (
            SELECT 
                sum(score) as new_trust_budget,
                max(rank) as cutoff_rank,
                channel_id
            FROM (
                SELECT
                fid,
                score,
                NTILE({NUM_NTILES}) OVER (
                    PARTITION BY channel_id
                        ORDER BY score DESC
                ) as ptile,
                    rank,
                channel_id
                FROM
                    k3l_channel_rank
                WHERE 
                    strategy_name='{STRATEGY}'
            )
            WHERE ptile <= {CUTOFF_NTILE}
            GROUP BY channel_id
        )
        INSERT INTO k3l_channel_points_bal_new 
            (fid, channel_id, balance, latest_earnings, latest_score, latest_adj_score, insert_ts, update_ts)
            SELECT 
                rk.fid,
                rk.channel_id,
                coalesce(bal.balance, 0) + ((rk.score * (2-bt.new_trust_budget)::numeric) * {TOTAL_POINTS}) as balance, 
                -- new_score = old_score + ((old_trust_budget - new_trust_budget) * old_score)
                -- new_score = old_score + ((1 - new_trust_budget) * old_score)
                -- new_score = old_score ( 1 + (1 - new_trust_budget))
                (rk.score * (2-bt.new_trust_budget)::numeric) * {TOTAL_POINTS} as latest_earnings,
                rk.score as latest_score,
                (rk.score * (2-bt.new_trust_budget)::numeric) as latest_adj_score,
                CASE 
                    WHEN bal.insert_ts IS NULL THEN now()
                    ELSE bal.insert_ts
                END as insert_ts,
                now() as update_ts
            FROM k3l_channel_rank as rk
            INNER JOIN points_budget AS bt  
                ON (bt.channel_id = rk.channel_id 
                    AND rk.rank <= bt.cutoff_rank
                    AND rk.strategy_name='{STRATEGY}')
            LEFT JOIN k3l_channel_points_bal AS bal 
                ON (bal.channel_id = rk.channel_id 
                    AND bal.fid = rk.fid
                    AND rk.strategy_name='{STRATEGY}')
            WHERE
                bal.update_ts IS NULL OR bal.update_ts < now() - interval '{ALLOC_INTERVAL}'
        UNION
            SELECT 
                bal.fid,
                bal.channel_id,
                bal.balance as balance, 
                bal.latest_earnings as latest_earnings,
                bal.latest_score as latest_score, 
                bal.latest_adj_score as latest_adj_score,
                bal.insert_ts,
                bal.update_ts
            FROM k3l_channel_points_bal as bal
            LEFT JOIN k3l_channel_rank AS rk 
                ON (bal.channel_id = rk.channel_id 
                    AND bal.fid = rk.fid
                    AND rk.strategy_name='{STRATEGY}')
            WHERE
                rk.fid IS NULL OR bal.update_ts > now() - interval '{ALLOC_INTERVAL}'
    """
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {create_sql}")
                cursor.execute(create_sql)
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Upserted rows: {cursor.rowcount}")
            with conn.cursor() as cursor:
                logger.info(f"Executing: {replace_sql}")
                cursor.execute(replace_sql)
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
            
@Timer(name="update_points_balance_v2")
def update_points_balance_v2(logger: logging.Logger, pg_dsn: str, timeout_ms: int):
    # WARNING - EXTREME CAUTION - be very careful with these variables
    OLD_TBL = "k3l_channel_points_bal_old"
    LIVE_TBL = "k3l_channel_points_bal"
    NEW_TBL = "k3l_channel_points_bal_new"
    INTERVAL = "1 day"
    STRATEGY = "60d_engagement"
    NUM_NTILES = 10
    CUTOFF_NTILE = 9
    TOTAL_POINTS = 10_000
    ALLOC_INTERVAL = '22 hours'
    # WARNING - EXTREME CAUTION

    create_sql = (
        f"DROP TABLE IF EXISTS {OLD_TBL};"
        f"CREATE TABLE {NEW_TBL} (LIKE {LIVE_TBL} INCLUDING ALL);"
    )

    replace_sql = (
        f"ALTER TABLE {LIVE_TBL} RENAME TO {OLD_TBL};"
        f"ALTER TABLE {NEW_TBL} RENAME TO {LIVE_TBL};"
    )

    insert_sql = f"""
        WITH
            cast_scores_by_fid as (
                SELECT
                hash as cast_hash,
                SUM(
                    (
                    -- (10 * fids.score * ci.casted)
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
                    channels.id as channel_id
                FROM k3l_recent_parent_casts as casts -- find original casts
                INNER JOIN k3l_cast_action as ci -- find all authors and engager fids
                ON (ci.cast_hash = casts.hash
                    AND casts.timestamp BETWEEN now() - interval '{INTERVAL}' AND now()
                        )
                INNER JOIN warpcast_channels_data as channels -- to be able to join with channel rank
                    ON (channels.url=casts.root_parent_url)
                INNER JOIN k3l_channel_rank as fids -- to get fid scores in a channel
                    ON (fids.fid = ci.fid 
                        AND fids.channel_id = channels.id
                        AND fids.strategy_name = '{STRATEGY}')
                INNER JOIN k3l_channel_points_allowlist as allo
                    ON (allo.channel_id = channels.id)
                WHERE 
                        casts.timestamp BETWEEN now() - interval '{INTERVAL}' AND now()
                GROUP BY casts.hash, ci.fid, channels.id
            ), 
            cast_scores AS (
            SELECT
                cast_hash,
                        channel_id,
                sum(power(cast_score,2)) as cast_score
            FROM cast_scores_by_fid
            WHERE cast_score > 0
            GROUP BY cast_hash, channel_id
            ),
            author_scores AS (
                SELECT
                    SUM(cast_scores.cast_score) as score,
                        fids.fid,
                    fids.channel_id
                FROM cast_scores
                INNER JOIN k3l_recent_parent_casts AS casts 
                    ON casts.hash = cast_scores.cast_hash
                INNER JOIN k3l_channel_rank AS fids 
                ON (casts.fid = fids.fid 
                    AND fids.channel_id=cast_scores.channel_id
                    AND fids.strategy_name = '{STRATEGY}')
                GROUP BY fids.fid, fids.channel_id
            ),
            points_budget AS (
            SELECT 
                sum(score) as budget,
                channel_id
            FROM (
                SELECT
                fid,
                score,
                NTILE({NUM_NTILES}) OVER (
                    PARTITION BY channel_id
                        ORDER BY score DESC
                ) as ptile,
                channel_id
                FROM
                    author_scores
            )
            WHERE ptile <= {CUTOFF_NTILE}
            GROUP BY channel_id
            )
        INSERT INTO k3l_channel_points_bal_new 
            (fid, channel_id, balance, latest_earnings, latest_score, latest_adj_score, insert_ts, update_ts)
            SELECT -- new fids with no previous balance and balances that are older than cutoff period
                authors.fid,
                authors.channel_id,
                COALESCE(bal.balance, 0) + ((authors.score / bt.budget::numeric) * {TOTAL_POINTS}) as balance, 
                (authors.score / bt.budget::numeric) * {TOTAL_POINTS} as latest_earnings,
                authors.score as latest_score, 
                (authors.score / bt.budget::numeric) as latest_adj_score,
                CASE 
                    WHEN bal.insert_ts IS NULL THEN now()
                    ELSE bal.insert_ts
                END as insert_ts,
                now() as update_ts
            FROM author_scores as authors
            INNER JOIN points_budget as bt on (bt.channel_id = authors.channel_id)
            LEFT JOIN k3l_channel_points_bal as bal on (bal.channel_id = authors.channel_id 
                                                        AND bal.fid = authors.fid)
            WHERE
                bal.update_ts IS NULL OR bal.update_ts < now() - interval '{ALLOC_INTERVAL}'
            UNION
            SELECT -- existing balances that are not getting updated or were updated within cutoff period
                bal.fid,
                bal.channel_id,
                bal.balance as balance, 
                bal.latest_earnings as latest_earnings,
                bal.latest_score as latest_score, 
                bal.latest_adj_score as latest_adj_score,
                bal.insert_ts,
                bal.update_ts
            FROM k3l_channel_points_bal as bal
            LEFT JOIN author_scores as authors on (bal.channel_id = authors.channel_id 
                                                AND bal.fid = authors.fid)
            WHERE
                authors.fid IS NULL OR bal.update_ts > now() - interval '{ALLOC_INTERVAL}'	
    """
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {create_sql}")
                cursor.execute(create_sql)
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Upserted rows: {cursor.rowcount}")
            with conn.cursor() as cursor:
                logger.info(f"Executing: {replace_sql}")
                cursor.execute(replace_sql)
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

@Timer(name="insert_tokens_log")
def insert_tokens_log(
    logger: logging.Logger, pg_dsn: str, timeout_ms: int, is_airdrop: bool = False
):
    points_col = "balance" if is_airdrop else "latest_earnings"

    insert_sql = f"""
        WITH latest_log AS (
            SELECT max(points_ts) as max_points_ts, channel_id, fid 
                FROM k3l_channel_tokens_log
            GROUP BY channel_id, fid
        )
        INSERT INTO k3l_channel_tokens_log
            (fid, channel_id, amt, latest_points, points_ts)
        SELECT 
            bal.fid,
            bal.channel_id,
            round(bal.{points_col},0) as amt,
            bal.{points_col} as latest_points,
            bal.update_ts as points_ts
        FROM k3l_channel_points_bal as bal
        LEFT JOIN latest_log as tlog 
            ON (tlog.channel_id = bal.channel_id AND tlog.fid = bal.fid
            AND tlog.max_points_ts = bal.update_ts)
        WHERE tlog.channel_id IS NULL
    """
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Inserted rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

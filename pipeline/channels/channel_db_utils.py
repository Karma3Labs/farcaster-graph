import logging
from typing import Callable
from enum import StrEnum
import tempfile

from timer import Timer
import time
from config import settings
from asyncpg.pool import Pool
import asyncpg
import psycopg2
import psycopg2.extras
import pandas as pd

class TokenDistStatus(StrEnum):
    NULL = 'NULL'
    SUBMITTED = 'submitted'
    SUCCESS = 'success'
    FAILURE = 'failure'


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
            INNER JOIN k3l_channel_rank AS fids ON ci.fid = fids.fid AND fids.channel_id = '{channel_id}'
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
   
@Timer(name="fetch_weighted_fid_scores_df")
def fetch_weighted_fid_scores_df(
    logger: logging.Logger, 
    pg_dsn: str, 
    timeout_ms: int,
    reply_wt: int,
    recast_wt: int,
    like_wt:int,
    cast_wt:int,
    model_names: list[str]
) -> pd.DataFrame:
    
    STRATEGY = "60d_engagement"
    INTERVAL = "1 day"


    sql_query = f"""
    WITH 
    included_channels AS (
        SELECT plog.channel_id, max(plog.insert_ts) as last_ts, any_value(channels.url) as url
        FROM k3l_channel_points_log as plog
        INNER JOIN warpcast_channels_data as channels
            ON (channels.id = plog.channel_id)
        WHERE 
            plog.insert_ts < now() - interval '{INTERVAL}'
            AND plog.model_name IN {tuple(model_names)}
        GROUP BY channel_id
    ),
    eligible_casts AS (
        SELECT
            casts.hash as cast_hash,
                actions.replied,
                actions.casted,
                actions.liked,
                actions.recasted,
                actions.fid,
                incl.channel_id as channel_id
        FROM k3l_recent_parent_casts as casts 
   			INNER JOIN included_channels as incl
   				ON (incl.url = casts.root_parent_url)
 	 			INNER JOIN k3l_cast_action as actions
      		ON (actions.cast_hash = casts.hash
          	AND actions.action_ts > incl.last_ts)
    ),
    cast_scores_by_channel_fid AS (
        SELECT
            actions.cast_hash,
            SUM(
                    + ({cast_wt} * ranks.score * actions.casted)
                    + ({reply_wt} * ranks.score * actions.replied)
                    + ({recast_wt} * ranks.score * actions.recasted)
                    + ({like_wt} * ranks.score * actions.liked)
                ) as cast_score,
            actions.channel_id as channel_id
        FROM eligible_casts as actions
        INNER JOIN k3l_channel_rank as ranks
            ON (ranks.fid = actions.fid 
                AND ranks.channel_id=actions.channel_id 
                AND ranks.strategy_name='{STRATEGY}')
        GROUP BY actions.channel_id, actions.cast_hash, ranks.fid
    ),
    cast_scores AS (
        SELECT
            cast_hash,
            channel_id,
            sum(cast_score) as cast_score
        FROM cast_scores_by_channel_fid
        WHERE cast_score > 0
        GROUP BY cast_hash, channel_id
    )
    SELECT
        casts.fid as fid,
        cast_scores.channel_id as channel_id,
        SUM(cast_scores.cast_score) as score
    FROM cast_scores
    INNER JOIN k3l_recent_parent_casts AS casts 
        ON casts.hash = cast_scores.cast_hash
    GROUP BY casts.fid, cast_scores.channel_id
    """
    with tempfile.TemporaryFile() as tmpfile:
        if settings.IS_TEST:
            copy_sql = f"COPY ({sql_query} LIMIT 100) TO STDOUT WITH CSV HEADER"
        else:
            copy_sql = f"COPY ({sql_query}) TO STDOUT WITH CSV HEADER"
        logger.debug(f"{copy_sql}")
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.copy_expert(copy_sql, tmpfile)
                tmpfile.seek(0)
                df = pd.read_csv(
                    tmpfile,
                    dtype={"fid": "Int32", "channel_id": "str", "score": "Float64"},
                )
                return df

@Timer(name="insert_reddit_points_log")
def insert_reddit_points_log(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    model_name: str,
    reply_wt: int,
    recast_wt: int,
    like_wt: int,
    cast_wt: int,
):
    CHANNEL_RANK_STRATEGY = "60d_engagement"
    INTERVAL = "1 day"
    CHANNEL_RANK_CUTOFF_RATIO = 2
    MAX_GLOBAL_RANK = 20_000
    GLOBAL_RANK_STRATEGY_ID = 9
    NUM_NTILES = 10
    CUTOFF_NTILE = 9

    insert_sql = f"""
    WITH 
    excluded_channels AS (
        -- IMPORTANT: don't generate points within last 23 hours
        SELECT distinct(channel_id) as channel_id 
        FROM k3l_channel_points_log
        WHERE 
            insert_ts > now() - interval '{INTERVAL}'
            AND model_name = '{model_name}'
    ),
    eligible_channel_rank AS (
        SELECT 
            ROUND(max(rank)/{CHANNEL_RANK_CUTOFF_RATIO},0) as max_rank, 
            strategy_name, 
            k3l_channel_rank.channel_id 
        FROM k3l_channel_rank
        WHERE strategy_name = '{CHANNEL_RANK_STRATEGY}'
        GROUP BY k3l_channel_rank.channel_id, strategy_name
        ),
    eligible_channel_actors AS (
        SELECT fid, eligible_channel_rank.channel_id 
        FROM k3l_channel_rank
        INNER JOIN eligible_channel_rank 
            ON (eligible_channel_rank.channel_id=k3l_channel_rank.channel_id
                AND eligible_channel_rank.max_rank > k3l_channel_rank.rank
            AND eligible_channel_rank.strategy_name = k3l_channel_rank.strategy_name)
        ),
    cast_scores AS (
        SELECT
            casts.hash as cast_hash,
                SUM(
                    + ({cast_wt} * actions.casted)
                    + ({reply_wt} * actions.replied)
                    + ({recast_wt} * actions.recasted)
                    + ({like_wt} * actions.liked)
                ) as cast_score,
                channels.id as channel_id
        FROM k3l_cast_action as actions 
            INNER JOIN k3l_recent_parent_casts as casts -- find all authors and engager fids
            ON (actions.cast_hash = casts.hash
                AND actions.action_ts BETWEEN now() - interval '{INTERVAL}' AND now()
                    )
        INNER JOIN warpcast_channels_data as channels
            ON (channels.url = casts.root_parent_url)
        INNER JOIN k3l_channel_rewards_config as config
            ON (config.channel_id = channels.id AND config.is_points = true)
        LEFT JOIN excluded_channels as excl
            ON (excl.channel_id = channels.id)	
        LEFT JOIN k3l_rank 
            ON (k3l_rank.profile_id = actions.fid 
            AND k3l_rank.strategy_id = {GLOBAL_RANK_STRATEGY_ID} 
            AND k3l_rank.rank <= {MAX_GLOBAL_RANK})
        LEFT JOIN eligible_channel_actors 
            ON (eligible_channel_actors.fid = actions.fid 
            AND eligible_channel_actors.channel_id=channels.id)   
        WHERE 
            excl.channel_id IS NULL AND
            (   k3l_rank.profile_id IS NOT NULL  -- author is either ranked
                OR 
                eligible_channel_actors.fid IS NOT NULL -- has engagement from a ranked user
            )
        GROUP BY channels.id, casts.hash
        ),
        author_scores AS (
        SELECT
                SUM(cast_scores.cast_score) as score,
                    casts.fid,
                cast_scores.channel_id
            FROM cast_scores
            INNER JOIN k3l_recent_parent_casts AS casts 
                ON casts.hash = cast_scores.cast_hash
            GROUP BY casts.fid, cast_scores.channel_id
        ),
        top_ntile_authors AS (
        SELECT
            * 
        FROM (
            SELECT
            fid,
            score,
            NTILE({NUM_NTILES}) OVER (
                PARTITION BY channel_id
                    ORDER BY score DESC
            ) as ptile,
            channel_id
            FROM author_scores
                WHERE score > 0
        )
        WHERE ptile <= {CUTOFF_NTILE}
        )
    INSERT INTO k3l_channel_points_log (fid, channel_id, earnings, model_name, insert_ts)
    SELECT 
        authors.fid,
        authors.channel_id,
        authors.score as earnings,
        '{model_name}' as model_name,
        now() as insert_ts
    FROM author_scores as authors
    INNER JOIN top_ntile_authors as nt on (nt.channel_id = authors.channel_id and nt.fid = authors.fid)
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
                logger.info(f"Upserted rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")

@Timer(name="insert_genesis_points")
def insert_genesis_points(logger: logging.Logger, pg_dsn: str, timeout_ms: int):
    # WARNING - EXTREME CAUTION - be very careful with these variables
    STRATEGY = "60d_engagement" # TODO move this to k3l_channel_rewards_config
    GENESIS_BUDGET = 600_000
    # WARNING - EXTREME CAUTION
    insert_sql = f"""
        WITH 
        excluded_channels AS (
            -- IMPORTANT: don't airdrop for channels with existing balances
            SELECT distinct(channel_id) as channel_id 
            FROM k3l_channel_points_bal
        ),
        eligible_fids AS (
            SELECT
                rk.fid,
                rk.score as score,
                rk.channel_id,
                rk.score * {GENESIS_BUDGET} as earnings
            FROM k3l_channel_rank as rk
            INNER JOIN k3l_channel_rewards_config as config
                ON (config.channel_id = rk.channel_id AND config.is_points = true)
            LEFT JOIN excluded_channels as excl
                ON (excl.channel_id = rk.channel_id)
            WHERE excl.channel_id IS NULL AND rk.strategy_name='{STRATEGY}'
        )
        INSERT INTO k3l_channel_points_bal 
            (fid, channel_id, balance, latest_earnings, latest_score, latest_adj_score)
        SELECT 
            fids.fid, fids.channel_id, fids.earnings, fids.earnings, fids.score, fids.score
        FROM eligible_fids as fids
    """
    start_time = time.perf_counter()
    try:
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


@Timer(name="update_points_balance_v5")
def update_points_balance_v5(logger: logging.Logger, pg_dsn: str, timeout_ms: int):
    OLD_TBL = "k3l_channel_points_bal_old"
    LIVE_TBL = "k3l_channel_points_bal"
    NEW_TBL = "k3l_channel_points_bal_new"
    POINTS_MODEL = "cbrt_weighted"

    create_sql = (
        f"DROP TABLE IF EXISTS {OLD_TBL};"
        f"CREATE TABLE {NEW_TBL} (LIKE {LIVE_TBL} INCLUDING ALL);"
    )

    insert_sql = f"""
        WITH 
        last_channel_bal_ts AS (
            SELECT max(update_ts) as update_ts, channel_id
            FROM {LIVE_TBL}
            GROUP BY channel_id
        ),
        eligible_fids AS (
            SELECT 
                plog.fid,
                plog.channel_id,
                SUM(plog.earnings) as weekly_earnings,
                0 as score, -- TODO drop this column
                0 as adj_score -- TODO drop this column
            FROM k3l_channel_points_log AS plog
            INNER JOIN last_channel_bal_ts
                ON (last_channel_bal_ts.channel_id=plog.channel_id 
                    AND plog.model_name='{POINTS_MODEL}'
                    AND plog.insert_ts > last_channel_bal_ts.update_ts
                    )
            GROUP BY plog.fid, plog.channel_id
        )
        INSERT INTO {NEW_TBL} 
            (fid, channel_id, balance, latest_earnings, latest_score, latest_adj_score, insert_ts, update_ts)
            SELECT -- existing fids and new fids (hence coalesce)
                fids.fid,
                fids.channel_id,
                coalesce(bal.balance,0) + fids.weekly_earnings as balance,
                fids.weekly_earnings as latest_earnings,
                fids.score,
                fids.adj_score,
                coalesce(bal.insert_ts, now()) as insert_ts,
                now() as update_ts
            FROM eligible_fids as fids
            LEFT JOIN {LIVE_TBL} as bal
                ON (bal.channel_id = fids.channel_id
                    AND bal.fid = fids.fid)
            UNION
            SELECT -- existing balances with no points log since last balance update
                bal.fid,
                bal.channel_id,
                bal.balance as balance, 
                bal.latest_earnings as latest_earnings,
                bal.latest_score as latest_score, 
                bal.latest_adj_score as latest_adj_score,
                bal.insert_ts,
                bal.update_ts
            FROM {LIVE_TBL} AS bal
            LEFT JOIN eligible_fids AS fids 
                ON (bal.channel_id = fids.channel_id 
                    AND bal.fid = fids.fid)
            WHERE
                fids.fid IS NULL	
    """

    replace_sql = (
        f"ALTER TABLE {LIVE_TBL} RENAME TO {OLD_TBL};"
        f"ALTER TABLE {NEW_TBL} RENAME TO {LIVE_TBL};"
    )

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

@Timer(name="fetch_rewards_config_list")
def fetch_rewards_config_list(
    logger: logging.Logger, pg_dsn: str, timeout_ms: int, channel_id: str = None
) -> list[dict]:
    where_sql = "" if channel_id is None else f" WHERE channel_id = '{channel_id}'"
    select_sql = f"""
        SELECT 
            *
        FROM k3l_channel_rewards_config AS config
        {where_sql}
        ORDER BY channel_id
    """
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                logger.info(f"Executing: {select_sql}")
                cursor.execute(select_sql)
                rows = cursor.fetchall()
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return rows

@Timer(name="update_channel_token_status")
def update_channel_token_status(
    logger: logging.Logger, pg_dsn: str, timeout_ms: int, channel_id: str, is_tokens: bool 
) -> list[tuple[str, bool]]:
    update_sql = f"""
        UPDATE k3l_channel_rewards_config
        SET is_tokens = {'true' if is_tokens else 'false'} 
        WHERE channel_id = '{channel_id}'
    """
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            with conn.cursor() as cursor:
                logger.info(f"Executing: {update_sql}")
                cursor.execute(update_sql)
                logger.info(f"Inserted rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return

@Timer(name="get_next_dist_sequence")
def get_next_dist_sequence(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
) -> int:
    select_sql = "SELECT nextval('tokens_dist_seq')"
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(select_sql)
                    return cursor.fetchone()[0]
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return

@Timer(name="insert_tokens_log")
def insert_tokens_log(
    logger: logging.Logger, pg_dsn: str, timeout_ms: int, channel_id: str, reason:str, is_airdrop: bool = False
):
    # dist_id is fetched in separate transaction
    # but risk of gaps is not an issue 
    dist_id = get_next_dist_sequence (
                logger=logger,
                pg_dsn=pg_dsn,
                timeout_ms=timeout_ms,
    )
    if is_airdrop:
        insert_sql = f"""
        WITH 
        latest_verified_address as (
            SELECT (array_agg(v.claim->>'address' order by timestamp DESC))[1] as address, fid
            FROM verifications v
            WHERE deleted_at IS NULL
            AND claim->>'address' ~ '^(0x)?[0-9a-fA-F]{{40}}$'
            GROUP BY fid
        ),
        channel_totals AS (
            SELECT sum(balance) as balance, sum(latest_earnings) as latest_earnings, channel_id
            FROM k3l_channel_points_bal
            WHERE channel_id='{channel_id}' 
            GROUP BY channel_id
        )
        INSERT INTO k3l_channel_tokens_log
            (fid, fid_address, channel_id, amt, dist_id, dist_reason, latest_points, points_ts)
        SELECT 
            bal.fid,
            COALESCE(vaddr.address, encode(fids.custody_address,'hex')) as fid_address,
            bal.channel_id,
            round((bal.balance * config.token_airdrop_budget * (1 - config.token_tax_pct) / tot.balance),0) as amt,
            {dist_id} as dist_id,
            '{reason}' as dist_reason,
            bal.balance as latest_points,
            bal.update_ts as points_ts
        FROM k3l_channel_points_bal as bal
        INNER JOIN channel_totals as tot 
    		ON (tot.channel_id = bal.channel_id)
        INNER JOIN fids ON (fids.fid = bal.fid) 
        INNER JOIN k3l_channel_rewards_config as config
                ON (config.channel_id = bal.channel_id AND config.is_tokens = true)
        LEFT JOIN latest_verified_address as vaddr 
            ON (vaddr.fid=bal.fid)
        WHERE 
            bal.channel_id = '{channel_id}'
            AND bal.balance > 0
        ORDER BY channel_id, amt DESC
        """
    else:
        CLOSEST_SUNDAY = 'now()::DATE - EXTRACT(DOW FROM now())::INTEGER'

        insert_sql = f"""
            WITH latest_log AS (
                SELECT max(points_ts) as max_points_ts, channel_id, fid 
                FROM k3l_channel_tokens_log
                WHERE channel_id='{channel_id}'
                GROUP BY channel_id, fid
            ),
            latest_verified_address as (
                SELECT (array_agg(v.claim->>'address' order by timestamp DESC))[1] as address, fid
                FROM verifications v
                WHERE deleted_at IS NULL
                AND claim->>'address' ~ '^(0x)?[0-9a-fA-F]{{40}}$'
                GROUP BY fid
            ),
            channel_totals AS (
                SELECT sum(balance) as balance, sum(latest_earnings) as latest_earnings, channel_id
                FROM k3l_channel_points_bal
                WHERE channel_id='{channel_id}' 
                GROUP BY channel_id
            )
            INSERT INTO k3l_channel_tokens_log
                (fid, fid_address, channel_id, amt, dist_id, dist_reason, latest_points, points_ts)
            SELECT 
                bal.fid,
                COALESCE(vaddr.address, encode(fids.custody_address,'hex')) as fid_address,
                bal.channel_id,
                round(
                        (
                        bal.latest_earnings 
                        * config.token_daily_budget 
                        * 7 
                        * (1 - config.token_tax_pct) / tot.latest_earnings
                        )
                    ,0) as amt,
                {dist_id} as dist_id,
                '{reason}' as dist_reason,
                bal.latest_earnings as latest_points,
                bal.update_ts as points_ts
            FROM k3l_channel_points_bal as bal
            INNER JOIN channel_totals as tot 
                ON (tot.channel_id = bal.channel_id)
            LEFT JOIN latest_log as tlog 
                ON (
                    tlog.channel_id = bal.channel_id 
                    AND tlog.fid = bal.fid
                    AND 
                    ( 
                        tlog.max_points_ts = bal.update_ts
                        OR 
                        tlog.max_points_ts > {CLOSEST_SUNDAY}
                    )
                )
            INNER JOIN fids ON (fids.fid = bal.fid) 
            INNER JOIN k3l_channel_rewards_config as config
                    ON (config.channel_id = bal.channel_id AND config.is_tokens = true)
            LEFT JOIN latest_verified_address as vaddr 
                ON (vaddr.fid=bal.fid)
            WHERE tlog.channel_id IS NULL
            AND bal.channel_id = '{channel_id}'
            AND bal.latest_earnings > 0
            ORDER BY channel_id, amt DESC
        """
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, 
            options=f"-c statement_timeout={timeout_ms}"
        )  as conn: 
            if is_airdrop:
                with conn.cursor() as cursor:
                    update_sql = f"""
                        UPDATE k3l_channel_rewards_config
                        SET is_tokens = 'true'
                        WHERE channel_id = '{channel_id}'
                    """ 
                    logger.info(f"Executing: {update_sql}")
                    cursor.execute(update_sql)
                    logger.info(f"Updated channel rewards config for {channel_id}")
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Inserted rows: {cursor.rowcount} for {dist_id}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return dist_id

@Timer(name="fetch_distribution_entries")
def fetch_distribution_entries(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    batch_size: int = 1000,
    callbackFn: Callable[[tuple], None] = None,
):
    limit = 10 if settings.IS_TEST else 1_000_000
    select_sql = f"""
        SELECT 
            channel_id, fid, fid_address, amt 
        FROM k3l_channel_tokens_log
        WHERE dist_status is NULL
        ORDER BY channel_id, amt DESC
        LIMIT {limit} -- safety valve
    """
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(select_sql)
                    while True:
                        rows = cursor.fetchmany(batch_size)
                        if len(rows) == 0:
                            logger.info("No more rows to process")
                            break
                        if callbackFn is not None:
                            logger.info(f"Processing {len(rows)} rows")
                            callbackFn(rows)
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return

@Timer(name="fetch_distribution_ids")
def fetch_distribution_ids(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    status: TokenDistStatus,
):
    limit = 10 if settings.IS_TEST else 1_000_000
    match status:
        case TokenDistStatus.NULL:
            status_condn = " is NULL "
        case _:
            status_condn = f" = '{status}' " 
    select_sql = f"""
        SELECT 
            distinct channel_id, dist_id 
        FROM k3l_channel_tokens_log
        WHERE dist_status {status_condn}
        ORDER BY channel_id, dist_id
        LIMIT {limit} -- safety valve
    """
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(select_sql)
                    rows = cursor.fetchall()
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return rows

@Timer(name="fetch_distributions_one_channel")
def fetch_distributions_one_channel(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int
)-> tuple[str,list[dict]]:
    select_sql = """
        SELECT 
            channel_id, 
            dist_id,
            json_agg(
                json_build_object(
                'address', fid_address,
                'amount', amt
                )
            ) as distributions 
        FROM k3l_channel_tokens_log
        WHERE dist_status is NULL
        AND amt > 0
        AND fid_address IS NOT NULL
        GROUP BY channel_id, dist_id
        ORDER BY channel_id, dist_id
        LIMIT 1
    """
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(select_sql)
                    return cursor.fetchone()
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return


@Timer(name="update_distribution_status")
def update_distribution_status(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    dist_id: int,
    channel_id: str,
    txn_hash: str,
    old_status:TokenDistStatus,
    new_status:TokenDistStatus,
):
    match old_status:
        case TokenDistStatus.NULL:
            status_condn = " is NULL "
        case _:
            status_condn = f" = '{old_status}' " 
    match new_status:
        case TokenDistStatus.NULL:
            status_to = " NULL "
        case _:
            status_to = f"'{new_status}'"

    update_sql = f"""
        UPDATE k3l_channel_tokens_log
        SET dist_status = {status_to}, 
            txn_hash = {"'"+txn_hash+"'" if txn_hash else "NULL"}
        WHERE dist_status {status_condn} 
        AND channel_id = '{channel_id}'
        AND dist_id = {dist_id}
    """
    logger.info(f"Executing: {update_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(update_sql)
                    logger.info(f"Updated rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return

@Timer(name="update_token_bal")
def update_token_bal(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    dist_id: int,
    channel_id: str,
):
    update_sql = f"""
        WITH eligible_fids AS (
        SELECT 
                amt, channel_id, fid
            FROM k3l_channel_tokens_log
            WHERE dist_status = 'success' 
                AND channel_id = '{channel_id}'
            AND dist_id = {dist_id}
        )
        MERGE INTO k3l_channel_tokens_bal as bal
        USING eligible_fids as fids 
                    ON (bal.channel_id = fids.channel_id AND bal.fid = fids.fid)
        WHEN MATCHED THEN
            UPDATE SET 
            balance = balance + fids.amt, 
            latest_earnings = fids.amt, 
            update_ts = DEFAULT
        WHEN NOT MATCHED THEN
            INSERT 
            (fid, channel_id, balance, latest_earnings, insert_ts, update_ts)
        VALUES 
            (fids.fid, fids.channel_id, fids.amt, fids.amt, DEFAULT, DEFAULT);
    """
    logger.info(f"Executing: {update_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
                pg_dsn, 
                options=f"-c statement_timeout={timeout_ms}"
            )  as conn: 
                with conn.cursor() as cursor:
                    cursor.execute(update_sql)
                    logger.info(f"Updated rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return
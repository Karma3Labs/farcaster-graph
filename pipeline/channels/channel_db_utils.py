import datetime
import logging
import tempfile
import time
from contextlib import contextmanager
from enum import Enum, StrEnum

import asyncpg
import pandas as pd
import psycopg2
import psycopg2.extras
from asyncpg.pool import Pool
from sqlalchemy import create_engine

import db_utils
from config import settings
from db_utils import pyformat2format
from timer import Timer
from utils import dow_utc_time, last_dow_utc_time, pacific_9am_in_utc_time


@contextmanager
def connection_logged(dsn: str, logger: logging.Logger, timeout_ms: int | None = None):
    start_time = time.perf_counter()
    kwargs = {}
    if timeout_ms is not None:
        kwargs.update(options=f"-c statement_timeout={timeout_ms}")
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(dsn, **kwargs) as conn, conn.cursor() as cursor:
            yield cursor
    except Exception as e:
        logger.error(e)
        raise
    logger.info(f"db took {time.perf_counter() - start_time} secs")


class TokenDistStatus(StrEnum):
    NULL = "NULL"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    FAILURE = "failure"


class DOW(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


async def fetch_rows(*args, logger: logging.Logger, sql_query: str, pool: Pool):
    start_time = time.perf_counter()
    logger.debug(f"Execute query: {sql_query}")
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.debug):
                # Run the query passing the request argument.
                try:
                    rows = await connection.fetch(
                        sql_query, *args, timeout=settings.POSTGRES_TIMEOUT_SECS
                    )
                except Exception as e:
                    logger.error(f"Failed to execute query: {sql_query}")
                    logger.error(f"{e}")
                    return [{"Unknown error. Contact K3L team"}]
    logger.info(f"db took {time.perf_counter() - start_time} secs for {len(rows)} rows")
    return rows


@Timer(name="fetch_channel_mods_with_metrics")
def fetch_channel_mods_with_metrics(
    logger: logging.Logger, pg_url: str, since: str, notification_threshold: int
):
    sql_engine = create_engine(pg_url)
    try:
        with sql_engine.connect() as conn:
            select_sql = f"""
            WITH eligible AS (
                SELECT
                    channel_id,
                    sum(int_value) as int_value
                FROM k3l_channel_metrics
                WHERE metric_ts > GREATEST(now() - '7 days'::interval,
                                            '{since}'::timestamptz)
                AND metric = 'weekly_num_casts'
                GROUP BY channel_id
            )
            SELECT
                ch.id as channel_id,
                ARRAY(
                    SELECT DISTINCT fids
                    FROM unnest(ARRAY[leadfid] || moderatorfids) as fids
                ) as mods
            FROM warpcast_channels_data as ch
            INNER JOIN eligible
                    ON (ch.id = eligible.channel_id
                        and eligible.int_value > {notification_threshold}
                    )
            ORDER BY eligible.int_value desc
            """
            logger.debug(f"{select_sql}")
            df = pd.read_sql_query(select_sql, conn)
            return df
    except Exception as e:
        logger.error(f"Failed to fetch_channel_mods_with_metrics: {e}")
        raise e
    finally:
        sql_engine.dispose()


def fetch_channel_casters(
    logger: logging.Logger, pg_dsn: str, channel_url: str
) -> list[int]:
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


@Timer(name="filter_channel_followers")
async def filter_channel_followers(
    logger: logging.Logger,
    pg_dsn: str,
    channel_id: str,
    fids: list[int],
):
    sql_query = f"""
            SELECT fid
            FROM warpcast_followers
            WHERE channel_id = '{channel_id}'
            AND fid = ANY(ARRAY{list(fids)})
            """
    async with asyncpg.create_pool(pg_dsn, min_size=1, max_size=5) as pool:
        return await fetch_rows(logger=logger, sql_query=sql_query, pool=pool)


@Timer(name="fetch_channels_trend_score")
async def fetch_channels_trend_score(
    logger: logging.Logger,
    pg_dsn: str,
    channel_ids: list[str],
):
    sql_query = f"""
        WITH
        filtered_channels AS (
            SELECT
                id,
                url
            FROM warpcast_channels_data
            WHERE id = ANY(ARRAY{list(channel_ids)})
        ),
        top_fids AS (
            SELECT
                profile_id as fid, rank
            FROM
                k3l_rank
            WHERE strategy_id=9 AND rank <= 10000
        )
        SELECT
            ch.id,
            count(*) as score
        FROM k3l_recent_parent_casts AS casts
        INNER JOIN filtered_channels AS ch ON (ch.url = casts.root_parent_url)
        INNER JOIN top_fids ON (top_fids.fid = casts.fid
            AND casts.timestamp > now() - interval '1 day'
            AND casts.root_parent_url IS NOT NULL)
        GROUP BY ch.id
        ORDER BY score DESC
        """
    async with asyncpg.create_pool(pg_dsn, min_size=1, max_size=5) as pool:
        return await fetch_rows(logger=logger, sql_query=sql_query, pool=pool)


def prep_channel_rank_log(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    run_id: str,
    num_days: int,
    num_batches: int,
) -> int:
    lock_sql = """
        SELECT
            1
        FROM k3l_channel_rank_log
        WHERE rank_status = 'inprogress'
        LIMIT 1
        FOR UPDATE
    """

    update_sql = """
        UPDATE k3l_channel_rank_log
        SET rank_status = 'terminated'
        WHERE rank_status = 'pending'
    """

    insert_sql = f"""
    WITH batches AS (
        SELECT
            NTILE({num_batches}) OVER( ORDER BY random() ) as batch_id,
            id as channel_id
        FROM
            warpcast_channels_data
    )
    INSERT INTO k3l_channel_rank_log (run_id, num_days, channel_id, batch_id, rank_status)
    SELECT
        '{run_id}',
        {num_days},
        channel_id,
        batch_id,
        'pending'
    FROM
        batches
    """

    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing: {lock_sql}")
                cursor.execute(lock_sql)
                rows = cursor.fetchall()
                if len(rows) > 0:
                    logger.info("Channel rank log already in progress")
                    raise Exception("Channel ranking already in progress")
            with conn.cursor() as cursor:
                logger.info(f"Executing: {update_sql}")
                cursor.execute(update_sql)
                num_rows = cursor.rowcount
                logger.info(f"Expired rows: {num_rows}")
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                num_rows = cursor.rowcount
                logger.info(f"Inserted rows: {num_rows}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return num_rows


def update_channel_rank_batch_inprogress(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    run_id: str,
    num_days: int,
    batch_id: int,
) -> list[str]:
    update_sql = f"""
        UPDATE k3l_channel_rank_log
        SET rank_status = 'inprogress'
        WHERE
        rank_status = 'pending'
        AND run_id = '{run_id}'
        AND num_days = {num_days}
        AND batch_id = {batch_id}
        RETURNING channel_id
    """
    with connection_logged(pg_dsn, logger, timeout_ms=timeout_ms) as cursor:
        logger.info(f"Executing: {update_sql}")
        cursor.execute(update_sql)
        channel_ids = cursor.fetchall()
        logger.info(f"Updated rows: {len(channel_ids)}")
    return [channel_id[0] for channel_id in channel_ids] if channel_ids else []


def update_channel_rank_for_cid(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    run_id: str,
    num_days: int,
    batch_id: int,
    channel_id: str,
    num_fids: int,
    inactive_seeds: list[int],
    elapsed_time_ms: int,
    is_error: bool,
) -> list[str]:
    if is_error:
        status = "errored"
    else:
        status = "completed"
    update_sql = f"""
        UPDATE k3l_channel_rank_log
        SET
            rank_status = '{status}',
            num_fids = %(num_fids)s,
            inactive_seeds = %(inactive_seeds)s,
            elapsed_time_ms = %(elapsed_time_ms)s
        WHERE
        rank_status = 'inprogress'
        AND run_id = '{run_id}'
        AND num_days = {num_days}
        AND batch_id = {batch_id}
        AND channel_id = '{channel_id}'
        RETURNING channel_id
    """
    update_data = {
        "num_fids": num_fids,
        "inactive_seeds": inactive_seeds,
        "elapsed_time_ms": elapsed_time_ms,
    }
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing: {update_sql}")
                cursor.execute(update_sql, update_data)
                channel_ids = cursor.fetchall()
                logger.info(f"Updated rows: {len(channel_ids)}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return [channel_id[0] for channel_id in channel_ids] if channel_ids else []


def insert_channel_scores_df(
    logger: logging.Logger, cid: str, scores_df: pd.DataFrame, pg_url: str
):
    try:
        if settings.IS_TEST:
            logger.warning(f"Skipping database insertion for channel {cid}")
        else:
            logger.info(f"Inserting data into the database for channel {cid}")
            db_utils.df_insert_copy(
                pg_url=pg_url, df=scores_df, dest_tablename=settings.TBL_CHANNEL_FIDS
            )
    except Exception as e:
        logger.error(f"Failed to insert data into the database for channel {cid}: {e}")
        raise e
    return


@Timer(name="fetch_weighted_fid_scores_df")
def fetch_weighted_fid_scores_df(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    reply_wt: int,
    recast_wt: int,
    like_wt: int,
    cast_wt: int,
    model_names: list[str],
    allowlisted_only: bool,
    is_v1: bool,
    gapfill: bool,
    date_str: str,
) -> pd.DataFrame:
    strategy = "60d_engagement"
    interval = datetime.timedelta(days=1)
    tbl_name = f"k3l_cast_action{'_v1' if is_v1 else ''}"

    cutoff = pacific_9am_in_utc_time(date_str)

    if not gapfill:
        exclude_condition = f"""
            (
                -- IMPORTANT: don't generate points within last 23 hours
                (now() > %(cutoff)s AND insert_ts > %(cutoff)s)
                OR
                (now() < %(cutoff)s AND insert_ts > %(cutoff)s - %(interval)s)
            )
        """
    else:
        # if gapfill is 2025-04-04, skip channels that have been inserted between 2025-04-04 and 2025-04-05
        exclude_condition = f"""
            (
                -- IMPORTANT: don't generate points if normal distribution happened for that day
                -- or if gapfill has already happened
                ( insert_ts > %(cutoff)s
                AND insert_ts <= %(cutoff)s + %(interval)s
                AND notes IS NULL)
                OR notes = 'GAPFILL-' || %(date_str)s
            )
        """
    # noinspection SqlUnusedCte
    sql_query = f"""
    WITH
    excluded_channels AS (
        SELECT distinct(channel_id) as channel_id
        FROM k3l_channel_points_log
        WHERE
            {exclude_condition}
            AND model_name = ANY(%(model_names)s)
    ),
    eligible_casts AS (
        SELECT
            casts.hash as cast_hash,
                actions.replied,
                actions.casted,
                actions.liked,
                actions.recasted,
                actions.fid,
                channels.id as channel_id
        FROM {tbl_name} as actions
        INNER JOIN k3l_recent_parent_casts as casts -- to be able to join with warpcast_channels_data
            ON (actions.cast_hash = casts.hash
                AND actions.action_ts >= %(cutoff)s - %(interval)s
                AND actions.action_ts < %(cutoff)s
                    )
        INNER JOIN warpcast_channels_data as channels
            ON (channels.url = casts.root_parent_url)
        {
        (
            '''
            INNER JOIN k3l_channel_rewards_config as config
            ON (config.channel_id = channels.id AND config.is_points = true)'''
        )
        if allowlisted_only
        else ""
    }
        LEFT JOIN excluded_channels as excl
            ON (excl.channel_id = channels.id)
        WHERE excl.channel_id IS NULL
    ),
    cast_scores_by_channel_fid AS (
        SELECT
            actions.cast_hash,
            SUM(
                    + (%(cast_wt)s * ranks.score * actions.casted)
                    + (%(reply_wt)s * ranks.score * actions.replied)
                    + (%(recast_wt)s * ranks.score * actions.recasted)
                    + (%(like_wt)s * ranks.score * actions.liked)
                ) as cast_score,
            actions.channel_id as channel_id
        FROM eligible_casts as actions
        INNER JOIN k3l_channel_rank as ranks -- cura_hidden_fids already excluded in channel_rank
            ON (ranks.fid = actions.fid
                AND ranks.channel_id=actions.channel_id
                AND ranks.strategy_name=%(strategy)s)
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
    {"LIMIT 100" if settings.IS_TEST else ""}
    """
    sql_query, args = pyformat2format(
        sql_query,
        cutoff=cutoff,
        interval=interval,
        date_str=date_str,
        model_names=list(model_names),
        cast_wt=cast_wt,
        reply_wt=reply_wt,
        recast_wt=recast_wt,
        like_wt=like_wt,
        strategy=strategy,
    )

    with (
        tempfile.TemporaryFile() as tmpfile,
        psycopg2.connect(pg_dsn, options=f"-c statement_timeout={timeout_ms}") as conn,
        conn.cursor() as cursor,
    ):
        sql_query = cursor.mogrify(sql_query, args).decode()
        copy_sql = f"COPY ({sql_query}) TO STDOUT WITH CSV HEADER"
        logger.info(f"{copy_sql}")
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
    channel_rank_strategy = "60d_engagement"
    interval = "1 day"
    channel_rank_cutoff_ratio = 2
    max_global_rank = 20_000
    global_rank_strategy_id = 9
    num_ntiles = 10
    cutoff_ntile = 9

    insert_sql = f"""
    WITH
    excluded_channels AS (
        -- IMPORTANT: don't generate points within the last 23 hours
        SELECT distinct(channel_id) as channel_id
        FROM k3l_channel_points_log
        WHERE
            insert_ts > now() - interval '{interval}'
            AND model_name = '{model_name}'
    ),
    eligible_channel_rank AS (
        SELECT
            ROUND(max(rank)/{channel_rank_cutoff_ratio},0) as max_rank,
            strategy_name,
            k3l_channel_rank.channel_id
        FROM k3l_channel_rank
        WHERE strategy_name = '{channel_rank_strategy}'
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
                AND actions.action_ts BETWEEN now() - interval '{interval}' AND now()
                    )
        INNER JOIN warpcast_channels_data as channels
            ON (channels.url = casts.root_parent_url)
        INNER JOIN k3l_channel_rewards_config as config
            ON (config.channel_id = channels.id AND config.is_points = true)
        LEFT JOIN excluded_channels as excl
            ON (excl.channel_id = channels.id)
        LEFT JOIN k3l_rank
            ON (k3l_rank.profile_id = actions.fid
            AND k3l_rank.strategy_id = {global_rank_strategy_id}
            AND k3l_rank.rank <= {max_global_rank})
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
            NTILE({num_ntiles}) OVER (
                PARTITION BY channel_id
                    ORDER BY score DESC
            ) as ptile,
            channel_id
            FROM author_scores
                WHERE score > 0
        ) x
        WHERE ptile <= {cutoff_ntile}
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
    with connection_logged(pg_dsn, logger, timeout_ms=timeout_ms) as cursor:
        logger.info(f"Executing: {insert_sql}")
        cursor.execute(insert_sql)
        logger.info(f"Upserted rows: {cursor.rowcount}")


@Timer(name="insert_genesis_points")
def insert_genesis_points(logger: logging.Logger, pg_dsn: str, timeout_ms: int):
    # WARNING - EXTREME CAUTION - be very careful with these variables
    # TODO move these to k3l_channel_rewards_config
    # ...because there will be a product requirement at some point in the future
    # ...where we want to expose them to frontend
    strategy = "60d_engagement"
    genesis_budget = 600_000
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
                rk.score * {genesis_budget} as earnings
            FROM k3l_channel_rank as rk -- cura_hidden_fids already excluded in channel_rank
            INNER JOIN k3l_channel_rewards_config as config
                ON (config.channel_id = rk.channel_id AND config.is_points = true)
            LEFT JOIN excluded_channels as excl
                ON (excl.channel_id = rk.channel_id)
            WHERE excl.channel_id IS NULL AND rk.strategy_name='{strategy}'
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
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Inserted rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")


@Timer(name="update_points_balance_v5")
def update_points_balance_v5(
    logger: logging.Logger, pg_dsn: str, timeout_ms: int, allowlisted_only: bool
):
    old_tbl = "k3l_channel_points_bal_old"
    live_tbl = "k3l_channel_points_bal"
    new_tbl = "k3l_channel_points_bal_new"
    points_model = "cbrt_weighted"

    create_sql = (
        f"DROP TABLE IF EXISTS {old_tbl};"
        f"CREATE TABLE {new_tbl} (LIKE {live_tbl} INCLUDING ALL);"
    )

    if allowlisted_only:
        balance_baseline_check = f"""
            SELECT max(update_ts) as update_ts, channel_id
            FROM {live_tbl}
            GROUP BY channel_id
        """
    else:
        balance_baseline_check = f"""
            SELECT
                coalesce(max(bal.update_ts), to_timestamp(0)) as update_ts,
                ch.id as channel_id
            FROM warpcast_channels_data as ch
            LEFT JOIN {live_tbl} as bal on (bal.channel_id=ch.id)
            GROUP BY ch.id
        """

    # noinspection SqlConstantExpression
    insert_sql = f"""
        WITH
        last_channel_bal_ts AS (
            {balance_baseline_check}
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
                    AND plog.model_name='{points_model}'
                    AND plog.insert_ts > last_channel_bal_ts.update_ts
                    )
            GROUP BY plog.fid, plog.channel_id
        )
        INSERT INTO {new_tbl}
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
            LEFT JOIN {live_tbl} as bal
                ON (bal.channel_id = fids.channel_id
                    AND bal.fid = fids.fid)
            UNION
            SELECT -- existing balances with no points log since the last balance update
                bal.fid,
                bal.channel_id,
                bal.balance as balance,
                bal.latest_earnings as latest_earnings,
                bal.latest_score as latest_score,
                bal.latest_adj_score as latest_adj_score,
                bal.insert_ts,
                bal.update_ts
            FROM {live_tbl} AS bal
            LEFT JOIN eligible_fids AS fids
                ON (bal.channel_id = fids.channel_id
                    AND bal.fid = fids.fid)
            WHERE
                fids.fid IS NULL
    """

    replace_sql = (
        f"ALTER TABLE {live_tbl} RENAME TO {old_tbl};"
        f"ALTER TABLE {new_tbl} RENAME TO {live_tbl};"
    )
    if settings.IS_TEST:
        logger.info("Skipping update_points_balance_v5 in test mode")
        logger.info(f"Test Mode: create_sql: {create_sql}")
        logger.info(f"Test Mode: insert_sql: {insert_sql}")
        logger.info(f"Test Mode: replace_sql: {replace_sql}")
        return

    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
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
) -> list[psycopg2.extras.DictRow]:
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
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                logger.info(f"Executing: {select_sql}")
                cursor.execute(select_sql)
                rows = cursor.fetchall()
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return rows


@Timer(name="update_channel_rewards_config")
def update_channel_rewards_config(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    channel_id: str,
    symbol: str,
    total_supply: int,
    creator_cut: int,
    vesting_months: int,
    airdrop_pmil: int,
    community_supply: int,
    token_airdrop_budget: int,
    token_daily_budget: int,
):
    update_sql = """
        UPDATE k3l_channel_rewards_config
        SET
        symbol = %(symbol)s,
        token_airdrop_budget = %(token_airdrop_budget)s,
        token_daily_budget = %(token_daily_budget)s,
        total_supply = %(total_supply)s,
        creator_cut = %(creator_cut)s,
        vesting_months = %(vesting_months)s,
        airdrop_pmil = %(airdrop_pmil)s,
        community_supply = %(community_supply)s
        WHERE channel_id = %(channel_id)s
    """
    update_data = {
        "symbol": symbol,
        "token_airdrop_budget": token_airdrop_budget,
        "token_daily_budget": token_daily_budget,
        "total_supply": total_supply,
        "creator_cut": creator_cut,
        "vesting_months": vesting_months,
        "airdrop_pmil": airdrop_pmil,
        "community_supply": community_supply,
        "channel_id": channel_id,
    }
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing: {update_sql}")
                cursor.execute(update_sql, update_data)
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
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(select_sql)
                return cursor.fetchone()[0]
    except Exception as e:
        logger.error(e)
        raise e


@Timer(name="insert_tokens_log")
def insert_tokens_log(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    channel_id: str,
    reason: str,
    is_airdrop: bool = False,
    batch_size: int = 250,
):
    # dist_id is fetched in a separate transaction,
    # but the risk of gaps is not an issue
    dist_id = get_next_dist_sequence(
        logger=logger,
        pg_dsn=pg_dsn,
        timeout_ms=timeout_ms,
    )
    if is_airdrop:
        insert_sql = f"""
        WITH
        latest_verified_address as (
            SELECT
                coalesce('0x' || encode(profiles.primary_eth_address, 'hex'),
                    (array_agg(v.claim->>'address' order by timestamp DESC))[1]) as address,
                profiles.fid
            FROM profiles
            LEFT JOIN verifications as v ON (v.fid=profiles.fid and v.deleted_at is null)
            WHERE profiles.deleted_at IS NULL
            AND v.claim->>'address' ~ '^(0x)?[0-9a-fA-F]{{40}}$'
            GROUP BY profiles.fid, profiles.primary_eth_address
        ),
        channel_totals AS (
            SELECT
                sum(balance) as balance,
                sum(latest_earnings) as latest_earnings,
                count(*) as ct,
                channel_id
            FROM k3l_channel_points_bal
            WHERE channel_id='{channel_id}'
            GROUP BY channel_id
        )
        INSERT INTO k3l_channel_tokens_log
            (fid, fid_address, channel_id, amt, dist_id, batch_id, dist_reason, latest_points, points_ts)
        SELECT
            bal.fid,
            COALESCE(vaddr.address, '0x' ||encode(fids.custody_address,'hex')) as fid_address,
            bal.channel_id,
            round((bal.balance * config.token_airdrop_budget * (1 - config.token_tax_pct) / tot.balance),0) as amt,
            {dist_id} as dist_id,
            ntile(cast(ceil(tot.ct / {batch_size}::numeric) as int)) over (order by bal.fid) as batch_id,
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
        ORDER BY channel_id, batch_id, fid
        """
    else:
        token_cutoff_timestamp = (
            f"TO_TIMESTAMP('{dow_utc_time(DOW.MONDAY).strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
            " AT TIME ZONE 'UTC'"
        )
        end_timestamp = (
            f"TO_TIMESTAMP('{dow_utc_time(DOW.TUESDAY).strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
            " AT TIME ZONE 'UTC'"
        )
        begin_timestamp = (
            f"TO_TIMESTAMP('{last_dow_utc_time(DOW.TUESDAY).strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
            " AT TIME ZONE 'UTC'"
        )

        insert_sql = f"""
            WITH
            is_monday_pts_done AS (
                SELECT channel_id FROM k3l_channel_points_log
                WHERE channel_id = '{channel_id}'
                    AND model_name='cbrt_weighted'
                    AND insert_ts > ({token_cutoff_timestamp})
                LIMIT 1
            ),
            pts_distrib AS (
                SELECT
                    count(distinct plog.insert_ts) as num_distrib,
                    plog.channel_id
                FROM k3l_channel_points_log AS plog
                INNER JOIN is_monday_pts_done ON (plog.channel_id=is_monday_pts_done.channel_id)
                WHERE plog.channel_id = '{channel_id}'
                    AND plog.model_name='cbrt_weighted'
                    AND plog.insert_ts > (
                            SELECT max(points_ts) FROM k3l_channel_tokens_log WHERE channel_id = '{channel_id}'
                        )
                    AND plog.insert_ts > ({begin_timestamp})
                    AND plog.insert_ts < ({end_timestamp})
                GROUP BY plog.channel_id
            ),
            eligible AS (
                SELECT
                    plog.fid,
                    plog.channel_id,
                    sum(plog.earnings) as earnings,
                    max(plog.insert_ts) as latest_points_ts
                FROM k3l_channel_points_log as plog
                INNER JOIN is_monday_pts_done ON (plog.channel_id=is_monday_pts_done.channel_id)
                WHERE
                    plog.channel_id = '{channel_id}'
                    AND plog.insert_ts > (
                        SELECT max(points_ts) FROM k3l_channel_tokens_log WHERE channel_id = '{channel_id}'
                    )
                    AND plog.model_name='cbrt_weighted'
                    AND plog.insert_ts > ({begin_timestamp})
                    AND plog.insert_ts < ({end_timestamp})
                GROUP BY plog.fid, plog.channel_id
            ),
            tokens AS (
                SELECT
                    eligible.fid,
                    fids.custody_address,
                    eligible.channel_id,
                    round((
                        eligible.earnings * config.token_daily_budget * 7 * (1 - config.token_tax_pct)
                        / (10000 * pts_distrib.num_distrib))
                    ,0) as amt,
                    eligible.earnings as latest_points,
                    eligible.latest_points_ts as points_ts
                FROM eligible
                INNER JOIN pts_distrib ON (pts_distrib.channel_id = eligible.channel_id)
                INNER JOIN k3l_channel_rewards_config as config
                        ON (config.channel_id = eligible.channel_id AND config.is_tokens=true)
                INNER JOIN fids ON (fids.fid = eligible.fid)
                ORDER BY channel_id, fid DESC
            ),
            numfids AS (
                SELECT count(*) as ct, channel_id
                FROM tokens
                GROUP BY channel_id
            )
            INSERT INTO k3l_channel_tokens_log
                (fid, fid_address, channel_id, amt, dist_id, batch_id, dist_reason, latest_points, points_ts)
            SELECT
                tokens.fid,
                COALESCE(
                        '0x' || encode(any_value(profiles.primary_eth_address), 'hex'),
                        (array_agg(v.claim->>'address' order by timestamp DESC))[1],
                        '0x' || encode(any_value(custody_address),'hex')
                ) as fid_address,
                tokens.channel_id,
                max(amt) as amt,
                {dist_id},
                ntile(cast(ceil(max(numfids.ct) / {batch_size}::numeric) as int)) over (order by tokens.fid) as batch_id,
                '{reason}' as dist_reason,
                max(latest_points) as latest_points,
                max(points_ts) as points_ts
            FROM tokens
            INNER JOIN numfids ON (numfids.channel_id = tokens.channel_id)
            LEFT JOIN profiles ON (profiles.fid = tokens.fid AND profiles.deleted_at IS NULL)
            LEFT JOIN verifications as v
                    ON (v.fid=tokens.fid AND v.deleted_at IS NULL
                        AND v.claim->>'address' ~ '^(0x)?[0-9a-fA-F]{{40}}$')
            GROUP BY tokens.fid, tokens.channel_id
        """
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            if is_airdrop:
                with conn.cursor() as cursor:
                    update_sql = f"""
                        UPDATE k3l_channel_rewards_config
                        SET is_tokens = 'true'
                        WHERE channel_id = '{channel_id}'
                    """
                    logger.info(f"Executing: {update_sql}")
                    cursor.execute(update_sql)
                    logger.info(
                        f"Updated channel rewards config for channel: {channel_id}"
                    )
            with conn.cursor() as cursor:
                logger.info(f"Executing: {insert_sql}")
                cursor.execute(insert_sql)
                logger.info(f"Inserted rows: {cursor.rowcount} for dist_id:{dist_id}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return dist_id


# Some DB rows contain the ASCII version of the 0x address, convert them into proper addresses.
@Timer(name="fixup_tokens_log_addresses")
def fixup_tokens_log_addresses(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
):
    start_time = time.perf_counter()
    try:
        # start transaction 'with' context manager
        # ...transaction is committed on exit and rolled back on exception
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                update_sql = """
                    UPDATE k3l_channel_tokens_log
                    SET fid_address = convert_from(decode(substr(fid_address, 3), 'hex'), 'utf-8')
                    WHERE lower(fid_address) SIMILAR TO '0x3078(3[0-9]|[46][1-6]){40}'
                """
                logger.info(f"Executing: {update_sql}")
                cursor.execute(update_sql)
    except Exception as e:
        logger.error(e)
        raise
    logger.info(f"db took {time.perf_counter() - start_time} secs")


@Timer(name="fetch_notify_entries")
def fetch_notify_entries(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
) -> tuple[datetime.datetime, pd.DataFrame]:
    end_timestamp = (
        f"TO_TIMESTAMP('{dow_utc_time(DOW.TUESDAY).strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        " AT TIME ZONE 'UTC'"
    )
    begin_timestamp = (
        f"TO_TIMESTAMP('{last_dow_utc_time(DOW.TUESDAY).strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        " AT TIME ZONE 'UTC'"
    )

    entries = []
    limit = 10 if settings.IS_TEST else 1_000_000
    sql_batch_size = 2 if settings.IS_TEST else 10_000
    select_sql = f"""
        SELECT
            plog.fid,
            plog.channel_id,
            sum(plog.earnings) as earnings,
            coalesce(bool_or(config.is_tokens), false) as is_token
        FROM k3l_channel_points_log AS plog
        LEFT JOIN k3l_channel_rewards_config AS config
            ON (config.channel_id = plog.channel_id)
        WHERE
            plog.model_name='cbrt_weighted'
            AND plog.insert_ts > ({begin_timestamp})
            AND plog.insert_ts < ({end_timestamp})
        GROUP BY plog.channel_id, plog.fid
        ORDER BY plog.channel_id, plog.fid
        LIMIT {limit} -- safety valve
    """
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(select_sql)
                while True:
                    rows = cursor.fetchmany(sql_batch_size)
                    entries.extend(rows)
                    if len(rows) == 0:
                        logger.info("No more rows to process")
                        break
                columns = [desc[0] for desc in cursor.description]
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return dow_utc_time(DOW.MONDAY), pd.DataFrame(entries, columns=columns)


@Timer(name="fetch_distribution_ids")
def fetch_distribution_ids(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    status: TokenDistStatus,
):
    limit = 10 if settings.IS_TEST else 1_000_000
    status_cond = " is NULL " if status == TokenDistStatus.NULL else f" = '{status}' "
    select_sql = f"""
        SELECT
            distinct channel_id, dist_id, batch_id
        FROM k3l_channel_tokens_log
        WHERE dist_status {status_cond}
        ORDER BY channel_id, dist_id, batch_id
        LIMIT {limit} -- safety valve
    """
    logger.info(f"Executing: {select_sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
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
    logger: logging.Logger, pg_dsn: str, timeout_ms: int
) -> tuple[str, list[dict]]:
    select_sql = """
        SELECT
            channel_id,
            dist_id,
            batch_id,
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
        GROUP BY channel_id, dist_id, batch_id
        ORDER BY channel_id, dist_id, batch_id
        LIMIT 1
    """
    logger.info(f"Executing: {select_sql}")
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(select_sql)
                return cursor.fetchone()
    except Exception as e:
        logger.error(e)
        raise e


@Timer(name="update_distribution_status")
def update_distribution_status(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    dist_id: int,
    batch_id: int,
    channel_id: str,
    txn_hash: str,
    old_status: TokenDistStatus,
    new_status: TokenDistStatus,
):
    status_cond = (
        " is NULL " if old_status == TokenDistStatus.NULL else f" = '{old_status}'"
    )
    status_to = " NULL " if new_status == TokenDistStatus.NULL else f"'{new_status}'"

    update_sql = f"""
        UPDATE k3l_channel_tokens_log
        SET dist_status = {status_to},
            txn_hash = {"'" + txn_hash + "'" if txn_hash else "NULL"}
        WHERE dist_status {status_cond}
        AND channel_id = '{channel_id}'
        AND dist_id = {dist_id}
        AND batch_id = {batch_id}
    """
    with connection_logged(pg_dsn, logger, timeout_ms=timeout_ms) as cursor:
        logger.info(f"Executing: {update_sql}")
        cursor.execute(update_sql)
        logger.info(f"Updated rows: {cursor.rowcount}")


@Timer(name="update_token_bal")
def update_token_bal(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    dist_id: int,
    batch_id: int,
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
            AND batch_id = {batch_id}
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
    with connection_logged(pg_dsn, logger, timeout_ms=timeout_ms) as cursor:
        logger.info(f"Executing: {update_sql}")
        cursor.execute(update_sql)
        logger.info(f"Updated rows: {cursor.rowcount}")


class Metric(StrEnum):
    WEEKLY_NUM_CASTS = "weekly_num_casts"
    WEEKLY_UNIQUE_CASTERS = "weekly_unique_casters"


def _metric_sql_for_metric(metric: Metric) -> str:
    match metric:
        case Metric.WEEKLY_NUM_CASTS:
            return "count(1) as int_value"
        case Metric.WEEKLY_UNIQUE_CASTERS:
            return "count(distinct fid) as int_value"
        case _:
            raise ValueError(f"Unknown metric: {metric}")


@Timer(name="upsert_weekly_metrics")
def upsert_weekly_metrics(
    logger: logging.Logger,
    pg_dsn: str,
    timeout_ms: int,
    metric: Metric,
):
    metric_sql = _metric_sql_for_metric(metric)

    sql = f"""
        INSERT INTO k3l_channel_metrics (metric_ts, channel_id, metric, int_value)
        WITH time_vars as (
        SELECT
            utc_offset,
            end_week_9amoffset(now()::timestamp - '2 week'::interval, utc_offset) as start_excl_ts
        FROM pg_timezone_names WHERE LOWER(name) = 'america/los_angeles'
        )
        SELECT
            end_week_9amoffset(action_ts, time_vars.utc_offset) as metric_ts,
            channel_id,
            '{metric.value}' as metric,
            {metric_sql}
        FROM k3l_cast_action_v1 CROSS JOIN time_vars
        WHERE
            casted=1
            AND channel_id IS NOT NULL
            AND action_ts > time_vars.start_excl_ts
        GROUP BY channel_id, metric_ts
        ON CONFLICT (metric_ts, channel_id, metric)
        DO UPDATE SET
            int_value = EXCLUDED.int_value,
            insert_ts = DEFAULT
    """
    if settings.IS_TEST:
        logger.info("Skipping upsert_weekly_metrics in test mode")
        logger.info(f"Test Mode: sql: {sql}")
        return
    logger.info(f"Executing: {sql}")
    start_time = time.perf_counter()
    try:
        with psycopg2.connect(
            pg_dsn, options=f"-c statement_timeout={timeout_ms}"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                logger.info(f"Upserted rows: {cursor.rowcount}")
    except Exception as e:
        logger.error(e)
        raise e
    logger.info(f"db took {time.perf_counter() - start_time} secs")
    return


@Timer(name="get_top_channels_for_fid")
async def get_top_channels_for_fid(
    logger: logging.Logger, pool: asyncpg.Pool, fid: int
):
    sql_query = """
SELECT
  channel_id,
  SUM(casted * 2 + replied * 2 + recasted * 2 + liked * 1) as num_actions -- not changing the key name for compatibility with frontend
FROM
  k3l_cast_action_v1
WHERE
  fid = $1
  AND channel_id IS NOT NULL
  AND action_ts >= NOW() - INTERVAL '1 month'
  group by channel_id
  order by num_actions desc;
    """
    return await fetch_rows(fid, logger=logger, sql_query=sql_query, pool=pool)

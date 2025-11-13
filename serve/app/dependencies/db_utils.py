import json
import re
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from textwrap import dedent
from typing import Any, TypedDict

import asyncpg
import pytz
from asyncpg.pool import Pool
from cashews import cache
from eth_typing import ChecksumAddress
from eth_utils import to_bytes
from loguru import logger
from memoize.configuration import (
    DefaultInMemoryCacheConfiguration,
    MutableCacheConfiguration,
)
from memoize.wrapper import memoize
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.channel_model import (
    ChannelEarningsOrderBy,
    ChannelEarningsScope,
    ChannelEarningsType,
    ChannelFidType,
    ChannelPointsOrderBy,
)
from app.models.feed_model import CastScore, CastsTimeDecay, SortingOrder
from app.models.score_model import ScoreAgg, Voting, Weights

from ..config import DBVersion, settings
from .cache import pr
from .memoize_utils import EncodedMethodNameAndArgsExcludedKeyExtractor


class DOW(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


engine = create_async_engine(
    settings.postgres_async_uri.get_secret_value(),
    echo=settings.POSTGRES_ECHO,
    future=True,
    pool_size=max(5, settings.POSTGRES_POOL_SIZE),
)


def sql_for_agg(agg: ScoreAgg, score_expr: str) -> str:
    match agg:
        case ScoreAgg.SUM:
            return f"sum({score_expr})"
        case ScoreAgg.SUM_SQUARE:
            return f"sum(power({score_expr}, 2))"
        case ScoreAgg.RMS:
            return f"sqrt(avg(power({score_expr}, 2)))"
        case ScoreAgg.SUM_CUBE_ROOT:
            return f"sum(power({score_expr}, 1.0/3))"


def sql_for_decay(
    interval_expr: str,
    period: CastsTimeDecay | timedelta,
    base: float = 1 - (1 / 365),
) -> str:
    if isinstance(period, CastsTimeDecay):
        if period == CastsTimeDecay.NEVER:
            base = 1
        else:
            period = period.timedelta
    if base == 1:
        return "1"
    if not 0 < base <= 1:
        raise ValueError(f"invalid time decay base {base}")
    if period < timedelta():
        raise ValueError(f"invalid time decay period {period}")
    return f"""
            power(
                {base}::numeric,
                (EXTRACT(EPOCH FROM ({interval_expr})) / ({period.total_seconds()}))::numeric
            )
    """


def _9am_pacific_in_utc_time():
    pacific_tz = pytz.timezone("US/Pacific")
    pacific_9am_str = " ".join(
        [datetime.now(pacific_tz).strftime("%Y-%m-%d"), "09:00:00"]
    )
    pacific_time = pacific_tz.localize(
        datetime.strptime(pacific_9am_str, "%Y-%m-%d %H:%M:%S")
    )
    utc_time = pacific_time.astimezone(pytz.utc)
    return utc_time


def _dow_utc_timestamp_str(dow: DOW) -> str:
    utc_time = _9am_pacific_in_utc_time()
    res = utc_time - timedelta(days=utc_time.weekday() - dow.value)
    return (
        f"(TO_TIMESTAMP('{res.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        " AT TIME ZONE 'UTC')"
    )


def _last_dow_utc_timestamp_str(dow: DOW):
    utc_time = _9am_pacific_in_utc_time()
    res = utc_time - timedelta(days=utc_time.weekday() - dow.value + 7)
    return (
        f"(TO_TIMESTAMP('{res.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        " AT TIME ZONE 'UTC')"
    )


def quote_sql_str(value: str):
    return f"'{value.replace("'", "''")}'"


def literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        return quote_sql_str(value.isoformat(sep=" "))
    if isinstance(value, dict):
        return quote_sql_str(json.dumps(value, indent=0, ensure_ascii=False))
    if isinstance(value, list):
        return f"ARRAY[{', '.join(literal(element) for element in value)}]"
    if isinstance(value, tuple):
        return f"ROW({', '.join(literal(field) for field in value)})"
    if isinstance(value, str):
        return quote_sql_str(value)
    if isinstance(value, bytes):
        return quote_sql_str(rf"\x{value.hex()}")
    return quote_sql_str(str(value))


async def fetch_rows(*args, sql_query: str, pool: Pool) -> list[asyncpg.Record]:
    start_time = time.perf_counter()
    logger.debug(
        f"Execute query: {dedent(sql_query)}\nwith args: ({', '.join(literal(arg) for arg in args)})"
    )
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        logger.debug(
            f"db took {time.perf_counter() - start_time} secs for acquiring connection"
        )
        # Run the query passing the request argument.
        rows = await connection.fetch(
            sql_query, *args, timeout=settings.POSTGRES_TIMEOUT_SECS
        )
    logger.debug(
        f"db took {time.perf_counter() - start_time} secs for {len(rows)} rows"
    )
    return rows


async def get_handle_fid_for_addresses(addresses: list[str], pool: Pool):
    sql_query = """
    (
        SELECT
            verifications.claim->>'address' as address,
            profiles.username as username,
            verifications.fid as fid
        FROM verifications
        LEFT JOIN neynarv3.profiles ON (profiles.fid = verifications.fid)
        WHERE
            verifications.claim->>'address' = ANY($1::text[])
    UNION
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            profiles.username as username,
            fids.fid as fid
        FROM neynarv3.fids
        LEFT JOIN neynarv3.profiles ON (profiles.fid = fids.fid)
            WHERE
                '0x' || encode(fids.custody_address, 'hex') = ANY($1::text[])
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(addresses, sql_query=sql_query, pool=pool)


async def get_all_fid_addresses_for_handles(handles: list[str], pool: Pool):
    sql_query = """
    (
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            profiles.username as username,
            fids.fid as fid
        FROM neynarv3.fids
        LEFT JOIN neynarv3.profiles ON (profiles.fid = fids.fid)
        WHERE
            profiles.username = ANY($1::text[])
    UNION
        SELECT
            verifications.claim->>'address' as address,
            profiles.username as username,
            verifications.fid as fid
        FROM verifications
        LEFT JOIN neynarv3.profiles ON (profiles.fid = verifications.fid)
        WHERE
            profiles.username = ANY($1::text[])
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(handles, sql_query=sql_query, pool=pool)


async def get_unique_fid_metadata_for_handles(handles: list[str], pool: Pool):
    sql_query = """
    SELECT
        '0x' || encode(any_value(neynarv3.fids.custody_address), 'hex') as address,
        any_value(profiles.username) as username,
        fids.fid as fid
    FROM neynarv3.fids
    LEFT JOIN neynarv3.profiles ON (profiles.fid = fids.fid)
    WHERE
        profiles.username = ANY($1::text[])
    GROUP BY fids.fid
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(handles, sql_query=sql_query, pool=pool)


async def get_verified_addresses_for_fids(fids: list[str], pool: Pool):
    sql_query = """
    WITH latest_global_rank as (
        select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=9
                and date in (select max(date) from k3l_rank)
    ),
    verified_addresses as (
        SELECT
            verifications.claim->>'address' as address,
            fids.fid as fid,
            ROW_NUMBER() OVER(PARTITION BY verifications.fid
                                ORDER BY verifications.timestamp DESC) AS created_order
        FROM neynarv3.fids
        INNER JOIN verifications ON (verifications.fid = fids.fid)
        WHERE
            fids.fid = ANY($1::integer[])
    )
    SELECT
        vaddr.address as address,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT(profiles.username)), null) as usernames,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT(profiles.pfp_url)), null) as pfp,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT(profiles.bio)),null) as bios,
        vaddr.fid as fid
    FROM verified_addresses as vaddr
    LEFT JOIN neynarv3.profiles ON (profiles.fid = vaddr.fid)
    LEFT JOIN latest_global_rank as grank ON (grank.fid = vaddr.fid)
    WHERE created_order=1
    GROUP BY vaddr.fid, address
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)


async def get_all_handle_addresses_for_fids(fids: list[str], pool: Pool):
    sql_query = """
    WITH latest_global_rank as (
    select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=9
                and date in (select max(date) from k3l_rank)
    ),
    fid_details as
    (
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            profiles.username as username,
            profiles.pfp_url as pfp,
            profiles.bio as bio,
            fids.fid as fid
        FROM neynarv3.fids
        LEFT JOIN neynarv3.profiles ON (profiles.fid = fids.fid)
        WHERE
            fids.fid = ANY($1::integer[])
    UNION
        SELECT
            verifications.claim->>'address' as address,
            profiles.username as username,
            profiles.pfp_url as pfp,
            profiles.bio as bio,
            fids.fid as fid
        FROM neynarv3.fids
        INNER JOIN verifications ON (verifications.fid = fids.fid)
        LEFT JOIN neynarv3.profiles ON (profiles.fid = fids.fid)
        WHERE
            fids.fid = ANY($1::integer[])
    )
    SELECT fid_details.*,
    latest_global_rank.global_rank
    FROM fid_details
    LEFT JOIN latest_global_rank using(fid)
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)


async def get_unique_handle_metadata_for_fids(fids: list[str], pool: Pool):
    sql_query = """
    WITH
    latest_global_rank as (
    select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=9
                and date in (select max(date) from k3l_rank)
    ),
    addresses AS (
    SELECT fid,'0x' || encode(fids.custody_address, 'hex') as address
    FROM neynarv3.fids where fid=ANY($1::integer[])
    UNION ALL
    SELECT fid, v.claim->>'address' as address
    FROM verifications v where fid=ANY($1::integer[])
    ),
    agg_addresses as (
    SELECT fid,
    ARRAY_AGG(DISTINCT address) as address
    FROM addresses
    GROUP BY fid
    )
    SELECT agg_addresses.*,
        latest_global_rank.global_rank,
        ANY_VALUE(profiles.username) as username,
        ANY_VALUE(profiles.pfp_url)  as pfp,
        ANY_VALUE(profiles.bio) as bio
        from agg_addresses
    LEFT JOIN neynarv3.profiles ON (profiles.fid = agg_addresses.fid)
    LEFT JOIN latest_global_rank on (agg_addresses.fid = latest_global_rank.fid)
    GROUP BY agg_addresses.fid,agg_addresses.address,latest_global_rank.global_rank
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)


async def get_top_profiles(
    strategy_id: int, offset: int, limit: int, pool: Pool, query_type: str
):
    if query_type == "lite":
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
        )
        SELECT
            profile_id as fid,
            any_value(profiles.username) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN neynarv3.profiles on (profiles.fid = profile_id)
        WHERE strategy_id = $1
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        OFFSET $2
        LIMIT $3
        """
    elif query_type == "superlite":
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
        ),ranks as (
        SELECT
            profile_id as fid,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        WHERE strategy_id = $1
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        OFFSET $2
        LIMIT $3
        )
        select fid from ranks
        """
    else:
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
        )
        SELECT
            profile_id as fid,
            any_value(profiles.username) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN neynarv3.profiles on (profiles.fid = profile_id)
        WHERE strategy_id = $1
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        OFFSET $2
        LIMIT $3
        """
    return await fetch_rows(strategy_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_channel_stats(
    channel_id: str, strategy_name: str, openrank_manager_address: str, pool: Pool
):
    sql_query = """
    WITH
    follower_stats AS (
    SELECT
        channel_id,
            count(*) as num_followers
    FROM warpcast_followers
    WHERE channel_id = $1
    GROUP BY channel_id
    ),
    rank_stats AS (
    SELECT
        channel_id AS ranked_cid,
        COUNT(*) AS num_fids_ranked,
    --     PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY score) AS p25_score,
    --     PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY score) AS p50_score,
    --     PERCENTILE_DISC(0.75) WITHIN GROUP (ORDER BY score) AS p75_score,
    --     PERCENTILE_DISC(0.90) WITHIN GROUP (ORDER BY score) AS p90_score,
        MIN(score) as min_score,
        MAX(score) as max_score
    FROM k3l_channel_rank
    WHERE channel_id = $1
    AND strategy_name = $2
    GROUP BY channel_id
    ),
    member_stats AS (
    SELECT
        channel_id as member_cid,
            count(*) as num_members
    FROM warpcast_members
    WHERE channel_id = $1
    GROUP BY channel_id
    ),
    points_stats AS (
    SELECT
        channel_id as points_cid,
        count(fid) as num_holders,
    --     PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY balance) AS p25_balance,
    --     PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY balance) AS p50_balance,
    --     PERCENTILE_DISC(0.75) WITHIN GROUP (ORDER BY balance) AS p75_balance,
    --     PERCENTILE_DISC(0.90) WITHIN GROUP (ORDER BY balance) AS p90_balance,
        MIN(balance) as min_balance,
        MAX(balance) as max_balance
    FROM k3l_channel_points_bal
        WHERE channel_id = $1
    GROUP BY channel_id
    ),
    tokens_stats AS (
        SELECT
            channel_id as tokens_cid,
        count(fid) as token_num_holders,
    --     PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY balance) AS token_p25_balance,
    --     PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY balance) AS token_p50_balance,
    --     PERCENTILE_DISC(0.75) WITHIN GROUP (ORDER BY balance) AS token_p75_balance,
    --     PERCENTILE_DISC(0.90) WITHIN GROUP (ORDER BY balance) AS token_p90_balance,
        MIN(balance) as token_min_balance,
        MAX(balance) as token_max_balance
    FROM k3l_channel_tokens_bal
    WHERE channel_id = $1
    GROUP BY channel_id
    ),
    category_stats AS (
    SELECT
        channel_id as cat_cid,
        category
    FROM k3l_channel_categories
    WHERE channel_id = $1
    ),
    openrank_metadata AS (
    SELECT
        ocm.category as or_category,
        ocm.request_tx_hash,
        ocm.results_tx_hash,
        ocm.challenge_tx_hash,
        ocm.req_id
    FROM openrank_channel_metadata ocm
    WHERE EXISTS (SELECT 1 FROM k3l_channel_categories kcc WHERE kcc.channel_id = $1 AND kcc.category = ocm.category)
    AND ocm.openrank_manager_address = $3
    ORDER BY ocm.req_id DESC
    LIMIT 1
    )
    SELECT
    channel_id,
    num_followers,
    num_fids_ranked,
    --   p25_score,p50_score,p75_score,p90_score,
        min_score,max_score,
    num_members,
    num_holders,
    --   p25_balance,p50_balance,p75_balance,p90_balance,
        min_balance,max_balance,
    token_num_holders,
    --   token_p25_balance,token_p50_balance,token_p75_balance,token_p90_balance,
    token_min_balance,token_max_balance,
    cs.category,
    orm.request_tx_hash,
    orm.results_tx_hash,
    orm.challenge_tx_hash
    FROM rank_stats as rs
    LEFT JOIN follower_stats as fids
        ON (fids.channel_id = rs.ranked_cid)
    LEFT JOIN member_stats as ms
        ON (ms.member_cid = rs.ranked_cid)
    LEFT JOIN points_stats as ps
        ON (ps.points_cid = rs.ranked_cid)
    LEFT JOIN tokens_stats as ts
        ON (ts.tokens_cid = rs.ranked_cid)
    LEFT JOIN category_stats as cs
        ON (cs.cat_cid = rs.ranked_cid)
    LEFT JOIN openrank_metadata as orm
        ON (orm.or_category = cs.category)
    """
    return await fetch_rows(
        channel_id,
        strategy_name,
        openrank_manager_address,
        sql_query=sql_query,
        pool=pool,
    )


async def get_channel_cast_metrics(channel_id: str, pool: Pool):
    sql_query = """
    SELECT
        metric,
	    JSON_AGG(
            JSON_BUILD_OBJECT(
                'as_of_utc', metric_ts,
                'value', COALESCE(int_value, float_value)
            ) ORDER BY metric_ts DESC
        ) as values
    FROM k3l_channel_metrics
    WHERE channel_id = $1
    GROUP BY metric
    """
    return await fetch_rows(channel_id, sql_query=sql_query, pool=pool)


async def get_channel_fid_metrics(
    channel_id: str, fid_type: ChannelFidType, pool: Pool
):
    timestamp_col = "followedat" if fid_type == ChannelFidType.FOLLOWER else "memberat"
    table_name = (
        "warpcast_followers"
        if fid_type == ChannelFidType.FOLLOWER
        else "warpcast_members"
    )
    metric_name = (
        "cumulative_weekly_followers"
        if fid_type == ChannelFidType.FOLLOWER
        else "cumulative_weekly_members"
    )
    sql_query = f"""
    WITH
    time_vars as (
        SELECT
            utc_offset,
            end_week_9amoffset(now()::timestamp - '2 week'::interval, utc_offset) as start_excl_ts
        FROM pg_timezone_names WHERE LOWER(name) = 'america/los_angeles'
    ),
    metric as (
        SELECT
            channel_id,
            end_week_9amoffset(to_timestamp({timestamp_col})::timestamp, time_vars.utc_offset) as metric_ts,
            count(1) as int_value
        FROM {table_name} CROSS JOIN time_vars
        WHERE channel_id=$1
        GROUP BY channel_id, metric_ts
    ),
    metric_values as (
        SELECT
            metric_ts,
            sum(int_value) over (order by metric_ts rows between unbounded preceding and current row) as int_value
        FROM metric
    )
    SELECT
        '{metric_name}' as metric,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'as_of_utc', metric_ts,
                'value', int_value
            ) ORDER BY metric_ts DESC
        ) as values
    FROM metric_values
    """
    return await fetch_rows(channel_id, sql_query=sql_query, pool=pool)


async def get_top_channel_balances(
    channel_id: str,
    offset: int,
    limit: int,
    lite: bool,
    orderby: ChannelPointsOrderBy,
    pool: Pool,
):
    if orderby == ChannelPointsOrderBy.DAILY_POINTS:
        orderby = ChannelEarningsOrderBy.DAILY
    else:
        orderby = ChannelEarningsOrderBy.TOTAL
    return await get_top_channel_earnings(
        channel_id=channel_id,
        offset=offset,
        limit=limit,
        lite=lite,
        earnings_type=ChannelEarningsType.POINTS,
        orderby=orderby,
        pool=pool,
    )


async def get_top_channel_earnings(
    channel_id: str,
    offset: int,
    limit: int,
    lite: bool,
    earnings_type: ChannelEarningsType,
    orderby: ChannelEarningsOrderBy,
    pool: Pool,
):
    orderby_clause = "ORDER BY balance DESC, daily_earnings DESC"
    if orderby == ChannelEarningsOrderBy.DAILY:
        orderby_clause = "ORDER BY daily_earnings DESC, balance DESC"

    table_name = "k3l_channel_points_bal"
    if earnings_type == ChannelEarningsType.TOKENS:
        table_name = "k3l_channel_tokens_bal"

    if lite:
        sql_query = f"""
        SELECT
            bal.fid,
            bal.balance as balance,
            CASE
                WHEN (bal.update_ts < now() - interval '1 days') THEN 0
                WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                ELSE bal.latest_earnings
            END as daily_earnings,
            bal.latest_earnings as latest_earnings,
            bal.update_ts as bal_update_ts
        FROM {table_name} as bal
        WHERE
            bal.channel_id = $1
        {orderby_clause}
        OFFSET $2
        LIMIT $3
        """
    else:
        sql_query = f"""
        WITH addresses as (
            SELECT '0x' || encode(fids.custody_address, 'hex') as address, fid
            FROM neynarv3.fids
            UNION ALL
            SELECT v.claim->>'address' as address, fid
            FROM verifications v
        ),
        top_records as (
            SELECT
                bal.fid,
                profiles.username as username,
                profiles.pfp_url as pfp,
                profiles.bio as bio,
                bal.balance as balance,
                CASE
                    WHEN (bal.update_ts < now() - interval '1 days') THEN 0
                    WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                    ELSE bal.latest_earnings
                END as daily_earnings,
                bal.latest_earnings as latest_earnings,
                bal.update_ts as bal_update_ts
            FROM {table_name} as bal
            LEFT JOIN neynarv3.profiles on (profiles.fid = bal.fid)
            WHERE
                bal.channel_id = $1
            {orderby_clause}
        ),
        mapped_records as (
            SELECT top_records.*,addresses.address
            FROM top_records
            LEFT JOIN addresses using (fid)
        )
        SELECT
            fid,
            any_value(username) as username,
            any_value(pfp) as pfp,
            any_value(bio) as bio,
            ARRAY_AGG(DISTINCT address) as addresses,
            any_value(balance) as balance,
            any_value(daily_earnings) as daily_earnings,
            any_value(latest_earnings) as latest_earnings,
            any_value(bal_update_ts) as bal_update_ts
        FROM mapped_records
        GROUP BY fid
        {orderby_clause}
        OFFSET $2
        LIMIT $3
        """
    return await fetch_rows(channel_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_tokens_distribution_details(
    channel_id: str, dist_id: int, batch_id: int, offset: int, limit: int, pool: Pool
):
    # asyncpg does not support named parameters
    # ... so optional params is not pretty
    # ... sanitize int input and use pyformat
    dist_filter = (
        f" AND dist_id = {int(dist_id)} " if dist_id else " ORDER BY insert_ts DESC"
    )

    sql_query = f"""
    WITH
    dist_id AS (
        SELECT
            channel_id, dist_id, batch_id
        FROM k3l_channel_tokens_log
        WHERE channel_id=$1
        AND batch_id=$2
        {dist_filter}
        LIMIT 1
    ),
    distrib_rows AS (
        SELECT
            tlog.channel_id,
            tlog.dist_id,
            tlog.batch_id,
            tlog.fid,
            fid_address,
            profiles.username as username,
            profiles.pfp_url as pfp,
            profiles.bio as bio,
            tlog.amt,
            tlog.txn_hash
        FROM k3l_channel_tokens_log AS tlog
        INNER JOIN dist_id
            ON (tlog.channel_id = dist_id.channel_id
                AND dist_id.dist_id = tlog.dist_id
                AND dist_id.batch_id = tlog.batch_id)
        LEFT JOIN neynarv3.profiles on (profiles.fid = tlog.fid)
    )
    SELECT
        fid,
        any_value(channel_id) as channel_id,
        any_value(dist_id) as dist_id,
        any_value(batch_id) as batch_id,
        any_value(fid_address) as fid_address,
        any_value(username) as username,
        any_value(pfp) as pfp,
        any_value(bio) as bio,
        max(amt) as amt,
        any_value(txn_hash) as txn_hash
    FROM distrib_rows
    GROUP BY fid
    ORDER BY amt DESC
    OFFSET $3
    LIMIT $4
    """
    return await fetch_rows(
        channel_id, batch_id, offset, limit, sql_query=sql_query, pool=pool
    )


async def get_top_channels_for_fid(fid: int, pool: Pool):
    sql_query = """
SELECT
  channel_id,
  SUM(casted * 2 + replied * 2 + recasted * 2 + liked * 1) as num_actions -- not changing the key name for compatibility with frontend
FROM
  k3l_cast_action_v1
WHERE
  fid = $1
  AND channel_id IS NOT NULL
  AND action_ts >= NOW() - INTERVAL '1 week'
  group by channel_id
  order by num_actions desc;
    """
    return await fetch_rows(fid, sql_query=sql_query, pool=pool)


async def get_tokens_distribution_overview(
    channel_id: str, offset: int, limit: int, pool: Pool
):
    sql_query = """
    SELECT
        channel_id,
        dist_id,
        batch_id,
        count(distinct fid) as num_fids,
        any_value(txn_hash) as txn_hash,
        CASE
            when any_value(dist_status) is NULL THEN 'Pending'
            when any_value(dist_status) = 'submitted' THEN 'In Progress'
            when any_value(dist_status) = 'success' THEN 'Completed'
            when any_value(dist_status) ='failure' THEN 'Failed'
            else 'Unknown'
        END as dist_status,
        CASE
    	    when any_value(dist_reason) ~ 'airdrop' THEN 'Airdrop'
            when any_value(dist_reason) ~ 'manual'  THEN 'Manual'
            when any_value(dist_reason) ~ 'scheduled' THEN 'Scheduled'
     	    else 'Unknown'
        END as dist_reason,
        max(update_ts) as update_ts,
            sum(amt) as total_amt,
            max(amt) as max_amt,
        min(amt) as min_amt,
    PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY amt) AS median_amt
    FROM k3l_channel_tokens_log
    WHERE channel_id = $1
    GROUP BY channel_id, dist_id, batch_id
    ORDER BY dist_id DESC, batch_id
    OFFSET $2
    LIMIT $3
    """
    return await fetch_rows(channel_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_fid_channel_token_balance(channel_id: str, fid: int, pool: Pool):
    sql_query = """
        SELECT
		    fid,
            channel_id,
            balance,
            CASE
                WHEN (bal.update_ts < now() - interval '1 days') THEN 0
                WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                ELSE bal.latest_earnings
            END as earnings_today,
            bal.latest_earnings as last_earnings,
            update_ts as last_earnings_ts
        FROM k3l_channel_tokens_bal as bal
        WHERE channel_id = $1
        AND fid = $2
    """
    res = await fetch_rows(channel_id, fid, sql_query=sql_query, pool=pool)
    if len(res) > 0:
        return res[0]
    return None


async def get_points_distribution_preview(
    channel_id: str, offset: int, limit: int, pool: Pool
):
    sql_query = """
        WITH latest as (
            SELECT channel_id, model_name, max(insert_ts) as insert_ts
            FROM k3l_channel_points_log
            WHERE channel_id = $1
            GROUP BY channel_id, model_name
        )
        SELECT
            l.channel_id, l.fid,
            any_value(profiles.username) as username,
            any_value(profiles.pfp_url) as pfp,
            any_value(profiles.bio) as bio,
            any_value(case when l.model_name = 'default' then earnings end) as default_earnings,
            any_value(case when l.model_name = 'sqrt_weighted' then earnings end) as sqrt_earnings,
            any_value(case when l.model_name = 'cbrt_weighted' then earnings end) as cbrt_earnings,
            any_value(case when l.model_name = 'reddit_default' then earnings end) as reddit_earnings,
            any_value(case when l.model_name = 'reddit_cast_weighted' then earnings end) as reddit_cast_weighted_earnings
        FROM k3l_channel_points_log as l
        INNER JOIN latest
            on (
                latest.channel_id = l.channel_id
            and latest.model_name = l.model_name
            and latest.insert_ts <= l.insert_ts
            )
        LEFT JOIN neynarv3.profiles on (profiles.fid = l.fid)
        GROUP BY l.channel_id, l.fid
        ORDER BY default_earnings desc NULLS LAST
        OFFSET $2
        LIMIT $3
        """
    return await fetch_rows(channel_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_tokens_distribution_preview(
    channel_id: str, offset: int, limit: int, scope: ChannelEarningsScope, pool: Pool
):
    if scope == ChannelEarningsScope.AIRDROP:
        points_col = "balance"
        interval_cond = ""
    else:
        points_col = "latest_earnings"
        interval_cond = " AND bal.update_ts > now() - interval '23 hours'"

    sql_query = f"""
        WITH latest_log AS (
            SELECT max(points_ts) as max_points_ts, channel_id, fid
            FROM k3l_channel_tokens_log
            WHERE channel_id = $1
            GROUP BY channel_id, fid
        ),
        latest_verified_address AS (
            SELECT (array_agg(v.claim->>'address' order by timestamp))[1] as address, fid
            FROM verifications v
            GROUP BY fid
        ),
        eligible AS (
            SELECT
                bal.fid as fid,
                COALESCE(vaddr.address, encode(fids.custody_address,'hex')) as fid_address,
                profiles.username as username,
                profiles.pfp_url as pfp,
                profiles.bio as bio,
                bal.channel_id as channel_id,
                round(bal.{points_col},0) as amt
            FROM k3l_channel_points_bal as bal
            LEFT JOIN latest_log as tlog
                ON (tlog.channel_id = bal.channel_id AND tlog.fid = bal.fid
                    AND tlog.max_points_ts = bal.update_ts)
            INNER JOIN neynarv3.fids ON (fids.fid = bal.fid)
            LEFT JOIN latest_verified_address as vaddr
                ON (vaddr.fid=bal.fid)
            LEFT JOIN neynarv3.profiles on (profiles.fid = bal.fid)
            WHERE
                tlog.channel_id IS NULL
                AND bal.channel_id = $1
                {interval_cond}
        )
        SELECT
            fid,
            any_value(fid_address) as fid_address,
            any_value(username) as username,
            any_value(pfp) as pfp,
            any_value(bio) as bio,
            any_value(channel_id) as channel_id,
            max(amt) as amt
        FROM eligible
        GROUP BY fid
        ORDER BY amt DESC
        OFFSET $2
        LIMIT $3
        """
    return await fetch_rows(channel_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_top_channel_profiles(
    channel_id: str, strategy_name: str, offset: int, limit: int, lite: bool, pool: Pool
):
    if lite:
        sql_query = """
        SELECT
            ch.fid,
            rank
        FROM k3l_channel_rank as ch
        WHERE
            channel_id = $1
            AND strategy_name = $2
            AND rank > $3 AND rank <= ($3 + $4)
        ORDER BY rank
        """
    else:
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_channel_rank
            WHERE channel_id = $1
            AND strategy_name = $2
        ),
        addresses as (
            SELECT '0x' || encode(fids.custody_address, 'hex') as address, fid
            FROM neynarv3.fids
            UNION ALL
            SELECT v.claim->>'address' as address, fid
            FROM verifications v
        ),
        top_records as (
            SELECT
                ch.fid,
                profiles.username as username,
                profiles.pfp_url as pfp,
                profiles.bio as bio,
                rank,
                score,
                ((total.total - (rank - 1))*100 / total.total) as percentile,
                bal.balance as balance,
                CASE
                    WHEN (bal.update_ts < now() - interval '1 days') THEN 0
                    WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                    ELSE bal.latest_earnings
                END as daily_earnings,
                bal.latest_earnings as latest_earnings,
                bal.update_ts as bal_update_ts
            FROM k3l_channel_rank as ch
            CROSS JOIN total
            LEFT JOIN neynarv3.profiles on (profiles.fid = ch.fid)
            LEFT JOIN k3l_channel_points_bal as bal
                on (bal.channel_id=ch.channel_id and bal.fid=ch.fid)
            WHERE
                ch.channel_id = $1
                AND
                ch.strategy_name=$2
                AND rank > $3 AND rank <= ($3 + $4)
            ORDER BY rank
        ),
        mapped_records as (
            SELECT top_records.*,addresses.address
            FROM top_records
            LEFT JOIN addresses using (fid)
        )
        SELECT
            fid,
            any_value(username) as username,
            any_value(pfp) as pfp,
            any_value(bio) as bio,
            any_value(rank) as rank,
            any_value(score) as score,
            ARRAY_AGG(DISTINCT address) as addresses,
            any_value(balance) as balance,
            any_value(daily_earnings) as daily_earnings,
            any_value(latest_earnings) as latest_earnings,
            any_value(bal_update_ts) as bal_update_ts
        FROM mapped_records
        GROUP BY fid
        ORDER by rank
        """
    return await fetch_rows(
        channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool
    )


async def get_profile_ranks(strategy_id: int, fids: list[int], pool: Pool, lite: bool):
    if lite:
        sql_query = """
                WITH total AS (
                    SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
                )
                SELECT
                    profile_id as fid,
                    any_value(profiles.username) as username,
                    rank,
                    score,
                    ((total.total - (rank - 1))*100 / total.total) as percentile
                FROM k3l_rank
                CROSS JOIN total
                LEFT JOIN neynarv3.profiles on (profiles.fid = profile_id)
                WHERE
                    strategy_id = $1
                    AND profile_id = ANY($2::integer[])
                GROUP BY profile_id,rank,score,percentile
                ORDER BY rank
                """
    else:
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
        )
        SELECT
            profile_id as fid,
            any_value(profiles.username) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN neynarv3.profiles on (profiles.fid = profile_id)
        WHERE
            strategy_id = $1
            AND profile_id = ANY($2::integer[])
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        """
    return await fetch_rows(strategy_id, fids, sql_query=sql_query, pool=pool)


async def filter_channel_fids(
    channel_id: str, fids: list[int], filter_: ChannelFidType, pool: Pool
):
    if filter_ == ChannelFidType.FOLLOWER:
        table_name = "warpcast_followers"
    elif filter_ == ChannelFidType.MEMBER:
        table_name = "warpcast_members"
    else:
        return []
    sql_query = f"""
    SELECT fid
    FROM {table_name}
    WHERE channel_id = $1
    AND fid = ANY($2::integer[])
    """
    return await fetch_rows(channel_id, fids, sql_query=sql_query, pool=pool)


async def get_channel_profile_ranks(
    channel_id: str, strategy_name: str, fids: list[int], lite: bool, pool: Pool
):
    if lite:
        sql_query = """
        SELECT
            ch.fid,
            rank
        FROM k3l_channel_rank as ch
        WHERE
            channel_id = $1
            AND
            strategy_name = $2
            AND
            fid = ANY($3::integer[])
        ORDER BY rank
        """
    else:
        monday_utc_timestamp = _dow_utc_timestamp_str(DOW.MONDAY)
        tuesday_utc_timestamp = _dow_utc_timestamp_str(DOW.TUESDAY)
        last_tuesday_utc_timestamp = _last_dow_utc_timestamp_str(DOW.TUESDAY)

        sql_query = f"""
        WITH
        total AS (
            SELECT count(*) as total from k3l_channel_rank
            WHERE channel_id = $1
            AND strategy_name = $2
        ),
        top_records as (
            SELECT
                ch.fid,
                ch.channel_id,
                ch.rank as channel_rank,
                ch.score as channel_score,
                k3l_rank.rank as global_rank,
                ((total.total - (ch.rank - 1))*100 / total.total) as percentile,
                bal.balance as balance,
                tok.balance as token_balance,
                CASE
                    WHEN (plog.insert_ts < now() - interval '1 days') THEN 0
                    WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                    ELSE plog.earnings
                END as daily_earnings,
                0 as token_daily_earnings,
                CASE
                    WHEN (now() BETWEEN {monday_utc_timestamp} AND {tuesday_utc_timestamp}) THEN false
                    ELSE true
                END as is_weekly_earnings_available,
                CASE
                    WHEN (
                        now() BETWEEN {monday_utc_timestamp} AND {tuesday_utc_timestamp}
                        AND plog.insert_ts > {last_tuesday_utc_timestamp}
                        AND plog.insert_ts < {tuesday_utc_timestamp}
                    ) THEN plog.earnings
                END as latest_earnings,
                tok.latest_earnings as token_latest_earnings,
                CASE
                    WHEN (
                        (now() > {monday_utc_timestamp} AND plog.insert_ts > {tuesday_utc_timestamp})
                        OR
                        (now() < {monday_utc_timestamp} AND plog.insert_ts > {last_tuesday_utc_timestamp})
                    ) THEN plog.earnings
                    ELSE 0
                END as weekly_earnings,
                0 as token_weekly_earnings,
                bal.update_ts as bal_update_ts,
                true as is_points_launched,
                coalesce(config.is_tokens, false) as is_tokens_launched
            FROM k3l_channel_rank as ch
            CROSS JOIN total
            LEFT JOIN k3l_rank on (ch.fid = k3l_rank.profile_id and k3l_rank.strategy_id = 9)
            LEFT JOIN k3l_channel_points_bal as bal
                on (bal.channel_id=ch.channel_id and bal.fid=ch.fid)
            LEFT JOIN k3l_channel_tokens_bal as tok
            		on (tok.channel_id=ch.channel_id and tok.fid=ch.fid)
            LEFT JOIN k3l_channel_rewards_config as config
                on (config.channel_id = ch.channel_id)
            LEFT JOIN k3l_channel_points_log as plog
                on (plog.model_name='cbrt_weighted' AND plog.channel_id=ch.channel_id
                    AND plog.fid = ch.fid
                    AND plog.insert_ts > now() - interval '8 days')
            WHERE
                ch.channel_id = $1
                AND
                ch.strategy_name = $2
                AND
                ch.fid = ANY($3::integer[])
        ),
        bio_data AS (
          SELECT
                top_records.fid,
                any_value(profiles.username) as username,
                any_value(profiles.pfp_url) as pfp,
                any_value(profiles.bio) as bio,
                ARRAY_AGG(DISTINCT v.claim->>'address') as address
          FROM top_records
          LEFT JOIN neynarv3.profiles on (profiles.fid = top_records.fid)
          LEFT JOIN verifications v on (v.fid = top_records.fid and v.deleted_at is null)
          GROUP BY top_records.fid
        )
        SELECT
            top_records.fid,
            channel_id,
            any_value(username) as username,
            any_value(pfp) as pfp,
            any_value(bio) as bio,
            channel_rank as rank,
            max(channel_score) as score,
            global_rank,
            any_value(percentile) as percentile,
            any_value(address) as addresses,
            max(balance) as balance,
            max(token_balance) as token_balance,
            max(daily_earnings) as daily_earnings,
            max(token_daily_earnings) as token_daily_earnings,
            bool_and(is_weekly_earnings_available) as is_weekly_earnings_available,
            sum(latest_earnings) as latest_earnings,
            max(token_latest_earnings) as token_latest_earnings,
            sum(weekly_earnings) as weekly_earnings,
            max(token_weekly_earnings) as token_weekly_earnings,
            any_value(bal_update_ts) as bal_update_ts,
            bool_or(is_points_launched) as is_points_launched,
            bool_or(is_tokens_launched) as is_tokens_launched
        FROM top_records
        LEFT JOIN bio_data ON (bio_data.fid=top_records.fid)
        GROUP BY top_records.fid, channel_id, channel_rank, global_rank
        ORDER by channel_rank,global_rank NULLS LAST
        """
    return await fetch_rows(
        channel_id, strategy_name, fids, sql_query=sql_query, pool=pool
    )


async def get_top_frames(
    agg: ScoreAgg,
    weights: Weights,
    offset: int,
    limit: int,
    recent: bool,
    decay: bool,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "weights.score * weights.weight * weights.decay_factor")
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    decay_sql = sql_for_decay(
        "CURRENT_TIMESTAMP - labels.latest_cast_dt",
        CastsTimeDecay.DAY if decay else CastsTimeDecay.NEVER,
    )

    sql_query = f"""
    WITH weights AS
    (
        SELECT
            interactions.url,
            k3l_rank.score,
            case interactions.action_type
                when 'cast' then {weights.cast}
                when 'recast' then {weights.recast}
                else {weights.like}
                end as weight,
            {decay_sql} as decay_factor
        FROM k3l_recent_frame_interaction as interactions
        {time_filter_sql}
        INNER JOIN
            k3l_rank on (k3l_rank.profile_id = interactions.fid and k3l_rank.strategy_id=3)
    )
    SELECT
        weights.url as url,
        {agg_sql} as score
    FROM weights
    GROUP BY weights.url
    ORDER by score DESC
    OFFSET $1
    LIMIT $2
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_top_frames_with_cast_details(
    agg: ScoreAgg,
    weights: Weights,
    offset: int,
    limit: int,
    recent: bool,
    decay: bool,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "weights.score * weights.weight * weights.decay_factor")
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    decay_sql = sql_for_decay(
        "CURRENT_TIMESTAMP - labels.latest_cast_dt",
        CastsTimeDecay.DAY if decay else CastsTimeDecay.NEVER,
    )

    sql_query = f"""
    WITH weights AS
    (
        SELECT
            interactions.url,
            interactions.url_id,
            k3l_rank.score,
            case interactions.action_type
                when 'cast' then {weights.cast}
                when 'recast' then {weights.recast}
                else {weights.like}
                end as weight,
            {decay_sql} as decay_factor
        FROM k3l_recent_frame_interaction as interactions
        {time_filter_sql}
        INNER JOIN
            k3l_rank on (k3l_rank.profile_id = interactions.fid and k3l_rank.strategy_id=3)
    ),
    top_frames AS (
        SELECT
            weights.url as url,
            weights.url_id,
            {agg_sql} as score
        FROM weights
        GROUP BY weights.url, weights.url_id
        ORDER by score DESC
        OFFSET $1
        LIMIT $2
    )
    SELECT
	    top_frames.url,
        max(top_frames.score) as score,
        (array_agg(distinct('0x' || encode(casts.hash, 'hex'))))[1:100] as cast_hashes,
        (array_agg(
            'https://warpcast.com/'||
            profiles.username||
            '/0x' ||
            substring(encode(casts.hash, 'hex'), 1, 8)
        order by casts.created_at
        ))[1:$2] as warpcast_urls
    FROM top_frames
	INNER JOIN k3l_cast_embed_url_mapping as url_map on (url_map.url_id = top_frames.url_id)
    INNER JOIN neynarv3.casts on (casts.id = url_map.cast_id)
    INNER JOIN neynarv3.profiles on (profiles.fid = casts.fid)
    GROUP BY top_frames.url
    ORDER BY score DESC
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_neighbors_frames(
    agg: ScoreAgg,
    weights: Weights,
    voting: Voting,
    trust_scores: list[dict],
    limit: int,
    recent: bool,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "weights.score * weights.weight")

    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    wt_score_sql = "k3l_rank.score"
    wt_weight_sql = f"""
                        case interactions.action_type
                            when 'cast' then {weights.cast}
                            when 'recast' then {weights.recast}
                            else {weights.like}
                            end
                        """
    wt_group_by_sql = ""
    match voting:
        case Voting.SINGLE:
            wt_score_sql = "max(score)"
            wt_weight_sql = f"""
                            max(case interactions.action_type
                                when 'cast' then {weights.cast}
                                when 'recast' then {weights.recast}
                                else {weights.like}
                                end)
                            """
            wt_group_by_sql = "GROUP BY interactions.url, interactions.fid"

    sql_query = f"""
    WITH weights AS
    (
        SELECT
            interactions.url,
            interactions.fid,
            {wt_score_sql} as score,
            {wt_weight_sql} as weight
        FROM k3l_recent_frame_interaction as interactions
        {time_filter_sql}
        INNER JOIN json_to_recordset($1::json)
            AS trust(fid int, score numeric) ON (trust.fid = interactions.fid)
        {wt_group_by_sql}
    )
    SELECT
        weights.url as url,
        {agg_sql} as score,
        array_agg(distinct(weights.fid::integer)) as interacted_by_fids,
        array_agg(distinct(profiles.username)) as interacted_by_usernames
    FROM weights
    LEFT JOIN neynarv3.profiles on (profiles.fid = weights.fid)
    GROUP BY weights.url
    ORDER by score DESC
    LIMIT $2
    """
    return await fetch_rows(
        json.dumps(trust_scores), limit, sql_query=sql_query, pool=pool
    )


async def get_popular_neighbors_casts(
    agg: ScoreAgg,
    weights: Weights,
    trust_scores: list[dict],
    offset: int,
    limit: int,
    lite: bool,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    resp_fields = (
        "'0x' || encode(hash, 'hex') as cast_hash,"
        "DATE_TRUNC('hour', timestamp) as cast_hour, fid, timestamp, cast_score"
    )

    if not lite:
        resp_fields = f"""
            {resp_fields},
            text,
            embeds,
            mentions,
            fid,
            timestamp,
            cast_score
        """

    sql_query = f"""
        with fid_cast_scores as (
            SELECT
                ci.cast_hash,
                SUM(
                    (
                        ({weights.cast} * trust.score * ci.casted)
                        + ({weights.reply} * trust.score * ci.replied)
                        + ({weights.recast} * trust.score * ci.recasted)
                        + ({weights.like} * trust.score * ci.liked)
                    )
                    *
                    {
        sql_for_decay(
            "CURRENT_TIMESTAMP - action_ts",
            CastsTimeDecay.HOUR,
            base=(1 - 1 / (365 * 24)),
        )
    }
                ) as cast_score
            FROM json_to_recordset($1::json)
                AS trust(fid int, score numeric)
            INNER JOIN k3l_cast_action as ci
                ON (ci.fid = trust.fid
                    AND ci.action_ts BETWEEN now() - interval '5 days'
  										AND now() - interval '10 minutes')
            GROUP BY ci.cast_hash, ci.fid
            LIMIT 100000
        )
        , scores AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score
                FROM fid_cast_scores
                GROUP BY cast_hash
                --    OFFSET $2
                --    LIMIT $3
            ),
    cast_details as (
    SELECT
        casts.hash,
        casts.timestamp,
        casts.text,
        casts.embeds,
        casts.mentions,
        casts.fid,
        cast_score
    FROM k3l_recent_parent_casts as casts
    INNER JOIN scores on casts.hash = scores.cast_hash
    WHERE deleted_at IS NULL
    --    ORDER BY casts.timestamp DESC
    ORDER BY casts.timestamp DESC, scores.cast_score DESC
    OFFSET $2
    LIMIT $3
    )
    select {resp_fields} from cast_details
    """
    return await fetch_rows(
        json.dumps(trust_scores), offset, limit, sql_query=sql_query, pool=pool
    )


async def get_recent_neighbors_casts(
    trust_scores: list[dict], offset: int, limit: int, lite: bool, pool: Pool
):
    resp_fields = f"""cast_hash, fid, timestamp"""
    if not lite:
        resp_fields = f"""
            {resp_fields},
            'https://warpcast.com/'||
            fname||cast_hash as url,
            text,
            embeds,
            mentions,
            fid,
            timestamp,
            cast_score
        """
    sql_query = f"""
    with cast_details as (
        SELECT
            '0x' || encode(casts.hash, 'hex') as cast_hash,
            casts.fid,
            profiles.username,
            casts.text,
            casts.embeds,
            casts.mentions,
            casts.timestamp,
            {
        sql_for_decay(
            "CURRENT_TIMESTAMP - casts.timestamp",
            CastsTimeDecay.HOUR,
            base=(1 - 1 / (365 * 24)),
        )
    }
            * trust.score as cast_score,
        row_number() over(partition by date_trunc('hour', casts.timestamp) order by random()) as rn
        FROM k3l_recent_parent_casts as casts
        INNER JOIN  json_to_recordset($1::json)
            AS trust(fid int, score numeric)
                ON casts.fid = trust.fid
        {
        "LEFT" if lite else "INNER"
    } JOIN neynarv3.profiles ON (profiles.fid = casts.fid)
        WHERE casts.deleted_at IS NULL
        ORDER BY casts.timestamp DESC, cast_score desc
        OFFSET $2
        LIMIT $3
        )
        select {resp_fields} from cast_details order by rn
    """
    return await fetch_rows(
        json.dumps(trust_scores), offset, limit, sql_query=sql_query, pool=pool
    )


async def get_recent_casts_by_fids(
    fids: list[int], offset: int, limit: int, pool: Pool
):
    sql_query = """
        SELECT
            '0x' || encode( casts.hash, 'hex') as cast_hash
        FROM neynarv3.casts
        WHERE
            casts.fid = ANY($1::integer[])
        ORDER BY casts.timestamp DESC
        OFFSET $2
        LIMIT $3
        """

    return await fetch_rows(fids, offset, limit, sql_query=sql_query, pool=pool)


async def get_all_token_balances(
    token_address: bytes,
    pool: Pool,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Return (fid, value) rows for every holder of *token_address*,
    sorted by value descending.  If *limit* is supplied, only the first
    N rows are returned (useful for leaderboards).
    """
    sql_query = """
        SELECT fid, value
        FROM k3l_token_holding_fids
        WHERE token_address = $1::bytea
        ORDER BY value DESC
    """
    if limit is not None:
        sql_query += "\nLIMIT $2"
        return records2dicts(
            await fetch_rows(token_address, limit, sql_query=sql_query, pool=pool)
        )

    return records2dicts(
        await fetch_rows(token_address, sql_query=sql_query, pool=pool)
    )


async def get_token_balances(
    token_address: bytes, fids: Iterable[int], pool: Pool
) -> list[dict[str, Any]]:
    sql_query = f"""
        SELECT fid, value
        FROM k3l_token_holding_fids
        WHERE token_address = $1::bytea AND fid = ANY($2::bigint[])
    """
    return records2dicts(
        await fetch_rows(token_address, fids, sql_query=sql_query, pool=pool)
    )


class Fip2Token(TypedDict):
    """TypedDict for FIP-2 token search results."""

    chain_id: int
    address: str  # hex string with 0x prefix
    symbol: str
    description: str


async def search_fip2_tokens(
    term: str,
    pool: Pool,
    chain_id: int | None = None,
) -> list[Fip2Token]:
    """
    Search for FIP-2 tokens based on the search term.

    - If term starts with '0x' and is a full 40-char hex address: exact match on address
    - If term starts with '$': prefix match on symbol (with or without $ in DB)
    - Otherwise: case-insensitive substring match on description
    - If chain_id is provided, constrain search to that chain only
    """
    if term.startswith("0x") and len(term) == 42:  # 0x + 40 hex chars
        # Exact address match
        try:
            # Convert hex string to bytes for comparison
            address_bytes = bytes.fromhex(term[2:])
        except ValueError:
            # Invalid hex, return empty result
            return []

        sql, args = pyformat2dollar(
            """
            SELECT
                chain_id,
                '0x' || encode(address, 'hex') AS address,
                symbol,
                description
            FROM k3l.erc20_tokens
            WHERE address = %(address)s::bytea
                AND CASE WHEN %(chain_id)s::bigint IS NULL THEN TRUE ELSE chain_id = %(chain_id)s::bigint END
            """,
            address=address_bytes,
            chain_id=chain_id,
        )
    elif term.startswith("$"):
        # Symbol prefix match (handle both with and without $ in DB)
        symbol_prefix = term[1:]  # Remove the leading $
        sql, args = pyformat2dollar(
            """
            SELECT
                chain_id,
                '0x' || encode(address, 'hex') AS address,
                symbol,
                description
            FROM k3l.erc20_tokens
            WHERE (symbol ILIKE %(prefix_with_dollar)s || '%%'
                   OR symbol ILIKE %(prefix_without_dollar)s || '%%')
                AND CASE WHEN %(chain_id)s::bigint IS NULL THEN TRUE ELSE chain_id = %(chain_id)s::bigint END
            ORDER BY
                CASE
                    WHEN symbol ILIKE %(prefix_without_dollar)s || '%%' THEN 0
                    ELSE 1
                END,
                symbol
            """,
            prefix_with_dollar="$" + symbol_prefix,
            prefix_without_dollar=symbol_prefix,
            chain_id=chain_id,
        )
    else:
        # Description substring match (case-insensitive)
        sql, args = pyformat2dollar(
            """
            SELECT
                chain_id,
                '0x' || encode(address, 'hex') AS address,
                symbol,
                description
            FROM k3l.erc20_tokens
            WHERE description ILIKE '%%' || %(term)s || '%%'
                AND CASE WHEN %(chain_id)s::bigint IS NULL THEN TRUE ELSE chain_id = %(chain_id)s::bigint END
            ORDER BY description
            """,
            term=term,
            chain_id=chain_id,
        )

    rows = await pool.fetch(sql, *args)
    return [
        Fip2Token(
            chain_id=row["chain_id"],
            address=row["address"],
            symbol=row["symbol"],
            description=row["description"],
        )
        for row in rows
    ]


@pr.refresh(
    if_slower_than=settings.CACHE_SLOW_QUERY_THRESHOLD,
    in_=settings.CACHE_EARLY_TTL,
)
@cache.early(ttl=settings.CACHE_TTL, early_ttl=settings.CACHE_EARLY_TTL)
async def get_token_holder_casts(
    agg: ScoreAgg,
    weights: Weights,
    score_threshold: float,
    max_cast_age: timedelta,
    time_decay_base: float,
    time_decay_period: timedelta,
    token_address: bytes,
    min_balance: Decimal,
    sorting_order: SortingOrder,
    time_bucket_length: timedelta,
    limit_casts: int | None,
    pool: Pool,
) -> list[dict[str, Any]]:
    decay_sql = sql_for_decay(
        "$4 - ca.action_ts", time_decay_period, base=time_decay_base
    )
    agg_sql = sql_for_agg(
        agg,
        f"""
        h.value * (
            {weights.cast}   * ca.casted +
            {weights.recast} * ca.recasted +
            {weights.reply}  * ca.replied +
            {weights.like}   * ca.liked
        ) * {decay_sql}
    """,
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    min_timestamp = now - max_cast_age
    order_by = f"ORDER BY score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_by = f"ORDER BY score DESC"
        case SortingOrder.RECENT:
            order_by = f"ORDER BY timestamp DESC"
        case SortingOrder.TIME_BUCKET:
            order_by = f"ORDER BY time_bucket ASC, score DESC"
        case SortingOrder.HOUR:
            order_by = f"ORDER BY time_bucket ASC, score DESC"
            time_bucket_length = timedelta(hours=1)
        case SortingOrder.DAY:
            order_by = f"ORDER BY time_bucket ASC, score DESC"
            time_bucket_length = timedelta(days=1)
        case SortingOrder.BALANCE:
            order_by = f"ORDER BY time_bucket ASC, balance_raw DESC, score DESC"
            if limit_casts is None:
                limit_casts = 3
    if limit_casts is None:
        limit_casts_condition = ""
    else:
        limit_casts_condition = f"AND rn <= {limit_casts}"
    sql_query = f"""
                WITH cs AS (
                    SELECT
                        ca.cast_hash AS hash,
                        {agg_sql} AS score
                    FROM k3l_cast_action_v1 AS ca
                    JOIN k3l_token_holding_fids AS h USING (fid)
                    WHERE
                        action_ts BETWEEN $3::timestamp AND $4::timestamp AND
                        token_address = $1::bytea AND
                        value > 0 AND
                        fid NOT IN (SELECT fid FROM k3l_action_discounted_fids)
                    GROUP BY ca.cast_hash
                ),
                c AS (
                    SELECT
                        hash,
                        fid,
                        timestamp,
                        floor(extract(epoch from $4 - timestamp) / {time_bucket_length.total_seconds()}) AS time_bucket,
                        row_number() OVER (PARTITION BY floor(extract(epoch from $4 - timestamp) / {time_bucket_length.total_seconds()}), fid ORDER BY score DESC) AS rn,
                        value AS balance_raw,
                        cs.score AS score
                    FROM k3l_recent_parent_casts c
                    JOIN cs USING (hash)
                    JOIN k3l_token_holding_fids th USING (fid)
                    WHERE
                        c.timestamp BETWEEN $3::timestamp AND $4::timestamp AND
                        th.token_address = $1::bytea AND th.value >= $5
                )
                SELECT
                    '0x' || encode(hash, 'hex') AS cast_hash,
                    fid,
                    timestamp,
                    balance_raw,
                    score AS cast_score
                FROM c
                WHERE
                    score >= (SELECT percentile_cont($2) WITHIN GROUP (ORDER BY score DESC) FROM c)
                    {limit_casts_condition}
                {order_by}
                """

    return [
        dict(r)
        for r in await fetch_rows(
            token_address,
            score_threshold,
            min_timestamp,
            now,
            min_balance,
            sql_query=sql_query,
            pool=pool,
        )
    ]


# noinspection PyUnusedLocal
@pr.refresh(
    if_slower_than=settings.CACHE_SLOW_QUERY_THRESHOLD,
    in_=settings.CACHE_EARLY_TTL,
)
@cache.early(ttl=settings.CACHE_TTL, early_ttl=settings.CACHE_EARLY_TTL)
async def get_new_user_casts(
    channel_id: str,
    caster_age: timedelta,
    agg: ScoreAgg,
    weights: Weights,
    score_threshold: float,
    max_cast_age: timedelta,
    time_decay_base: float,
    time_decay_period: timedelta,
    sorting_order: SortingOrder,
    time_bucket_length: timedelta,
    limit_casts: int | None,
    pool: Pool,
) -> list[dict[str, Any]]:
    decay_sql = sql_for_decay(
        "$4 - ca.action_ts", time_decay_period, base=time_decay_base
    )
    agg_sql = sql_for_agg(
        agg,
        f"""
        car.score * (
            {weights.cast}   * ca.casted +
            {weights.recast} * ca.recasted +
            {weights.reply}  * ca.replied +
            {weights.like}   * ca.liked
        ) * {decay_sql}
    """,
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    min_timestamp = now - max_cast_age
    if limit_casts is None:  # TODO(ek) remove this
        limit_casts = 3
    if limit_casts is None:
        limit_casts_condition = ""
    else:
        limit_casts_condition = f"AND rn <= {limit_casts}"
    sql_query = f"""
                WITH new_users AS (
                    SELECT fid
                    FROM neynarv3.fids
                    WHERE created_at >= $4
                    UNION DISTINCT
                    SELECT fid
                    FROM neynarv3.channel_follows
                    WHERE channel_id = $1
                    GROUP BY fid
                    HAVING min(created_at) >= $4
                ),
                c AS (
                    SELECT
                        c.hash,
                        fid,
                        c.timestamp,
                        floor(extract(epoch from $4 - c.timestamp) / {time_bucket_length.total_seconds()}) AS time_bucket,
                        row_number() OVER (PARTITION BY floor(extract(epoch from $4 - c.timestamp) / {time_bucket_length.total_seconds()}), fid ORDER BY c.timestamp DESC) AS rn
                    FROM k3l_recent_parent_casts c
                    JOIN new_users USING (fid)
                    JOIN neynarv3.channels ch ON c.root_parent_url = ch.url
                    WHERE
                        c.timestamp BETWEEN $2::timestamp AND $3::timestamp AND
                        ch.channel_id = $1
                )
                SELECT
                    '0x' || encode(hash, 'hex') AS cast_hash,
                    fid,
                    timestamp
                FROM c
                WHERE
                    TRUE
                    {limit_casts_condition}
                ORDER BY timestamp DESC
                """

    return [
        dict(r)
        for r in await fetch_rows(
            channel_id,
            min_timestamp,
            now,
            now - caster_age,
            sql_query=sql_query,
            pool=pool,
        )
    ]


async def get_popular_degen_casts(
    agg: ScoreAgg,
    weights: Weights,
    offset: int,
    limit: int,
    sorting_order: str,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    ordering = (
        "casts.timestamp DESC"
        if sorting_order == "recent"
        else "date_trunc('day',c.timestamp) DESC, cast_score DESC"
    )

    sql_query = f"""
        WITH fid_cast_scores AS (
            SELECT
                ca.cast_hash, ca.fid, ca.casted, ca.replied, ca.recasted, ca.liked, dt.parent_timestamp as timestamp, scores.v,
                (
                    (
                        ({weights.cast} * scores.v * ca.casted)
                        + ({weights.reply} * scores.v * ca.replied)
                        + ({weights.recast} * scores.v * ca.recasted)
                        + ({weights.like} * scores.v * ca.liked)
                    )
                    *
                    {
        sql_for_decay(
            "CURRENT_TIMESTAMP - dt.parent_timestamp", CastsTimeDecay.HOUR, base=0.99
        )
    } -- After 24 hours: 0.78584693
                ) as cast_score
            FROM k3l_degen_tips dt
            INNER JOIN k3l_cast_action ca ON (ca.cast_hash = dt.parent_hash AND ca.action_ts = dt.parent_timestamp)
            INNER JOIN degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 scores ON scores.i = ca.fid
            WHERE dt.parent_timestamp BETWEEN now() - interval '2 days' AND now() - interval '10 minutes'
        ),
        filtered_actions AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score
            FROM fid_cast_scores
            WHERE cast_score * 100000000000 > 100
            GROUP BY cast_hash
        ),
        cast_details AS (
            SELECT
                '0x' || encode(fa.cast_hash, 'hex') as cast_hash,
                DATE_TRUNC('hour', c.timestamp) as cast_hour,
                c.text,
                c.embeds,
                c.mentions,
                c.fid,
                fa.cast_score,
                c.timestamp,
              row_number() over ( partition by date_trunc('day',c.timestamp) order by date_trunc('day',c.timestamp), cast_score ) row_num
            FROM filtered_actions fa
            INNER JOIN neynarv3.casts c ON (c.hash = fa.cast_hash)
            ORDER BY {ordering}
        )
        SELECT cast_hash, timestamp, cast_score, fid, text, embeds, mentions
        FROM cast_details
        WHERE row_num between $1 and $2;
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_channel_ids_for_fid(fid: int, limit: int, pool: Pool):
    sql_query = """
        SELECT
            channel_id
        FROM
            warpcast_followers
        WHERE
            fid=$1
        ORDER BY RANDOM()
        LIMIT $2
    """
    return await fetch_rows(fid, limit, sql_query=sql_query, pool=pool)


async def get_channel_url_for_channel_id(channel_id: str, pool: Pool):
    sql_query = """
        SELECT
            url
        FROM
            warpcast_channels_data
        WHERE
            id=$1
    """
    return await fetch_rows(channel_id, sql_query=sql_query, pool=pool)


@memoize(
    configuration=MutableCacheConfiguration.initialized_with(
        DefaultInMemoryCacheConfiguration()
    ).set_key_extractor(
        EncodedMethodNameAndArgsExcludedKeyExtractor(
            skip_first_arg_as_self=False, skip_args=[13], skip_kwargs=["pool"]
        )
    )
)
async def get_popular_channel_casts_lite(
    channel_id: str,
    channel_url: str,
    strategy_name: str,
    max_cast_age: str,
    agg: ScoreAgg,
    score_threshold: float,
    reactions_threshold: int,
    weights: Weights,
    time_decay: CastsTimeDecay,
    normalize: bool,
    offset: int,
    limit: int,
    sorting_order: SortingOrder,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    order_sql = "cast_score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_sql = "cast_score DESC"
        case SortingOrder.RECENT:
            order_sql = "cast_ts DESC"
        case SortingOrder.HOUR:
            order_sql = "age_hours ASC, cast_score DESC"
        case SortingOrder.DAY:
            order_sql = "age_days ASC, cast_score DESC"
        case SortingOrder.REACTIONS:
            order_sql = "reaction_count DESC, cast_score DESC"

    decay_sql = sql_for_decay("CURRENT_TIMESTAMP - ci.action_ts", time_decay)

    if normalize:
        fid_score_sql = "cbrt(fids.score)"
    else:
        fid_score_sql = "fids.score"

    sql_query = f"""
        with fid_cast_scores as (
            SELECT
                hash as cast_hash,
                SUM(
                    (
                        ({weights.cast} * {fid_score_sql} * ci.casted)
                        + ({weights.reply} * {fid_score_sql} * ci.replied)
                        + ({weights.recast} * {fid_score_sql} * ci.recasted)
                        + ({weights.like} * {fid_score_sql} * ci.liked)
                    )
                    *
                    {decay_sql}
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts > now() - interval '{max_cast_age}'
                    AND casts.root_parent_url = $2)
            INNER JOIN k3l_channel_rank as fids
                ON (fids.channel_id=$1 AND fids.fid = ci.fid AND fids.strategy_name=$3)
            LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
            LEFT JOIN cura_hidden_fids as hids ON (hids.hidden_fid=ci.fid AND hids.channel_id=$1)
            WHERE md.affected_userid IS NULL AND hids.hidden_fid IS NULL
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts DESC
            LIMIT 100000
        )
        , scores AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score,
                MIN(cast_ts) as cast_ts,
                COUNT (*) - 1 as reaction_count
            FROM fid_cast_scores
            GROUP BY cast_hash
        )
    SELECT
        '0x' || encode(cast_hash, 'hex') as cast_hash,
        FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/3600) as age_hours,
        FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/(60 * 60 * 24)::numeric) AS age_days,
        cast_ts,
        cast_score
    FROM scores
    WHERE
        cast_score >= {score_threshold}
        AND reaction_count >= {reactions_threshold}
    ORDER BY {order_sql}
    OFFSET $4
    LIMIT $5
    """
    return await fetch_rows(
        channel_id,
        channel_url,
        strategy_name,
        offset,
        limit,
        sql_query=sql_query,
        pool=pool,
    )


# TODO deprecate in favor of get_popular_channel_casts_lite
async def get_popular_channel_casts_heavy(
    channel_id: str,
    channel_url: str,
    strategy_name: str,
    max_cast_age: str,
    agg: ScoreAgg,
    score_threshold: float,
    reactions_threshold: int,
    weights: Weights,
    time_decay: CastsTimeDecay,
    normalize: bool,
    offset: int,
    limit: int,
    sorting_order: SortingOrder,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    order_sql = "cast_score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_sql = "cast_score DESC"
        case SortingOrder.RECENT:
            order_sql = "cast_ts DESC"
        case SortingOrder.HOUR:
            order_sql = "age_hours ASC, cast_score DESC"
        case SortingOrder.DAY:
            order_sql = "age_days ASC, cast_score DESC"
        case SortingOrder.REACTIONS:
            order_sql = "reaction_count DESC, cast_score DESC"

    decay_sql = sql_for_decay("CURRENT_TIMESTAMP - ci.action_ts", time_decay)

    if normalize:
        fid_score_sql = "cbrt(fids.score)"
    else:
        fid_score_sql = "fids.score"

    sql_query = f"""
        with fid_cast_scores as (
            SELECT
                hash as cast_hash,
                SUM(
                    (
                        ({weights.cast} * {fid_score_sql} * ci.casted)
                        + ({weights.reply} * {fid_score_sql} * ci.replied)
                        + ({weights.recast} * {fid_score_sql} * ci.recasted)
                        + ({weights.like} * {fid_score_sql} * ci.liked)
                    )
                    *
                    {decay_sql}
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts > now() - interval '{max_cast_age}'
                    AND casts.root_parent_url = $2)
            INNER JOIN k3l_channel_rank as fids
                ON (fids.channel_id=$1 AND fids.fid = ci.fid AND fids.strategy_name=$3)
            LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
            LEFT JOIN cura_hidden_fids as hids ON (hids.hidden_fid=ci.fid AND hids.channel_id=$1)
            WHERE md.affected_userid IS NULL AND hids.hidden_fid IS NULL
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts desc
            LIMIT 100000
        )
        , scores AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score,
                COUNT (*) - 1 as reaction_count
            FROM fid_cast_scores
            GROUP BY cast_hash
        )
    SELECT
        '0x' || encode(casts.hash, 'hex') as cast_hash,
        FLOOR(EXTRACT(EPOCH FROM (now() - casts.timestamp))/3600) as age_hours,
        FLOOR(EXTRACT(EPOCH FROM (now() - casts.timestamp))/(60 * 60 * 24)::numeric) AS age_days,
        casts.text,
        casts.embeds,
        casts.mentions,
        casts.fid,
        casts.timestamp as cast_ts,
        cast_score,
        reaction_count
    FROM k3l_recent_parent_casts as casts
    INNER JOIN scores on casts.hash = scores.cast_hash
    WHERE
        cast_score >= {score_threshold}
        AND reaction_count >= {reactions_threshold}
    ORDER BY {order_sql}
    OFFSET $4
    LIMIT $5
    """
    return await fetch_rows(
        channel_id,
        channel_url,
        strategy_name,
        offset,
        limit,
        sql_query=sql_query,
        pool=pool,
    )


async def get_trending_casts_lite(
    agg: ScoreAgg,
    weights: Weights,
    score_threshold_multiplier: int,
    offset: int,
    limit: int,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    sql_query = f"""
        with
        latest_global_rank as (
        select profile_id as fid, score from k3l_rank g where strategy_id=3
            and date in (select max(date) from k3l_rank)
            and rank <= 15000
        ),
        fid_cast_scores as (
            SELECT
                hash as cast_hash,
                SUM(
                    (
                        ({weights.cast} * fids.score * ci.casted)
                        + ({weights.reply} * fids.score * ci.replied)
                        + ({weights.recast} * fids.score * ci.recasted)
                        + ({weights.like} * fids.score * ci.liked)
                    )
                    *
                    {
        sql_for_decay(
            "CURRENT_TIMESTAMP - ci.action_ts",
            CastsTimeDecay.HOUR,
            base=(1 - 1 / (365 * 24)),
        )
    }
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts BETWEEN now() - interval '3 days'
  										AND now() - interval '10 minutes')
            INNER JOIN latest_global_rank as fids ON (fids.fid = ci.fid )
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts desc
            LIMIT 100000
        )
        , scores AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score,
                MIN(cast_ts) as cast_ts
            FROM fid_cast_scores
            GROUP BY cast_hash
        ),
    cast_details as (
    SELECT
        '0x' || encode(cast_hash, 'hex') as cast_hash,
        DATE_TRUNC('hour', cast_ts) as cast_hour,
        row_number() over(partition by date_trunc('hour',cast_ts) order by random()) as rn
    FROM scores
    WHERE cast_score*{score_threshold_multiplier}>1
    ORDER BY  cast_hour DESC,cast_score DESC
    OFFSET $1
    LIMIT $2)
    select cast_hash,cast_hour from cast_details order by rn
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_trending_casts_heavy(
    agg: ScoreAgg,
    weights: Weights,
    score_threshold_multiplier: int,
    offset: int,
    limit: int,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    sql_query = f"""
        with
        latest_global_rank as (
        select profile_id as fid, score from k3l_rank g where strategy_id=3
            and date in (select max(date) from k3l_rank)
            and rank <= 15000
        )
        , fid_cast_scores as (
            SELECT
                hash as cast_hash,
                SUM(
                    (
                        ({weights.cast} * fids.score * ci.casted)
                        + ({weights.reply} * fids.score * ci.replied)
                        + ({weights.recast} * fids.score * ci.recasted)
                        + ({weights.like} * fids.score * ci.liked)
                    )
                    *
                    {
        sql_for_decay(
            "CURRENT_TIMESTAMP - ci.action_ts",
            CastsTimeDecay.HOUR,
            base=(1 - 1 / (365 * 24)),
        )
    }
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts BETWEEN now() - interval '3 days'
  										AND now() - interval '10 minutes')
            INNER JOIN latest_global_rank as fids ON (fids.fid = ci.fid )
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts desc
            LIMIT 1000000
        )
        , scores AS (
            SELECT
                cast_hash,
                {agg_sql} as cast_score
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
        row_number() over(partition by DATE_TRUNC('hour', casts.timestamp) order by random()) as rn
    FROM k3l_recent_parent_casts as casts
    INNER JOIN scores on casts.hash = scores.cast_hash
    WHERE cast_score*{score_threshold_multiplier}>1
    ORDER BY cast_hour DESC, cast_score DESC
    OFFSET $1
    LIMIT $2
    )
    select cast_hash,cast_hour,text,embeds,mentions,fid,timestamp,cast_score from cast_details order by rn
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_top_casters(offset: int, limit: int, pool: Pool):
    sql_query = """ select cast_hash, i as fid, v as score from k3l_top_casters
                    where date_iso = (select max(date_iso) from k3l_top_casters)
                    order by v desc
                    OFFSET $1 LIMIT $2"""
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_top_spammers(offset: int, limit: int, pool: Pool):
    sql_query = """ select
                    fid,
                    display_name,
                    total_outgoing,
                    spammer_score,
                    total_parent_casts,
                    total_replies_with_parent_hash,
                    global_openrank_score,
                    global_rank,
                    total_global_rank_rows
                    from k3l_top_spammers
                    where date_iso = (select max(date_iso) from k3l_top_spammers)
                    order by global_rank
                    OFFSET $1 LIMIT $2"""
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_top_channel_followers(
    channel_id: str, strategy_name: str, offset: int, limit: int, pool: Pool
):
    monday_utc_timestamp = _dow_utc_timestamp_str(DOW.MONDAY)
    tuesday_utc_timestamp = _dow_utc_timestamp_str(DOW.TUESDAY)
    last_tuesday_utc_timestamp = _last_dow_utc_timestamp_str(DOW.TUESDAY)

    sql_query = f"""
    WITH
    distinct_warpcast_followers as (
    SELECT
    	distinct
        fid,
        channel_id
    FROM warpcast_followers
    WHERE channel_id = $1
    {
        "AND insert_ts=(select max(insert_ts) FROM warpcast_followers where channel_id=$1)"
        if settings.DB_VERSION == DBVersion.EIGEN2
        else ""
    }
    ),
    followers_data as (
    SELECT
        wf.fid,
        wf.channel_id,
        klcr.rank as channel_rank,
        klcr.score as channel_score,
        k3l_rank.rank as global_rank,
        warpcast_members.memberat,
        bal.balance as balance,
        tok.balance as token_balance,
        CASE
            WHEN (plog.insert_ts < now() - interval '1 days') THEN 0
            WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
            ELSE plog.earnings
        END as daily_earnings,
        0 as token_daily_earnings,
        CASE
            WHEN (now() BETWEEN {monday_utc_timestamp} AND {
        tuesday_utc_timestamp
    }) THEN false
            ELSE true
        END as is_weekly_earnings_available,
        CASE
            WHEN (
                now() BETWEEN {monday_utc_timestamp} AND {tuesday_utc_timestamp}
                AND plog.insert_ts > {last_tuesday_utc_timestamp}
                AND plog.insert_ts < {tuesday_utc_timestamp}
            ) THEN plog.earnings
        END as latest_earnings,
        tok.latest_earnings as token_latest_earnings,
        CASE
            WHEN (
                    (now() > {monday_utc_timestamp} AND plog.insert_ts > {
        tuesday_utc_timestamp
    })
                    OR
                    (now() < {monday_utc_timestamp} AND plog.insert_ts > {
        last_tuesday_utc_timestamp
    })
                ) THEN plog.earnings
            ELSE 0
        END as weekly_earnings,
        0 as token_weekly_earnings,
        bal.update_ts as bal_update_ts,
        true as is_points_launched,
        coalesce(config.is_tokens, false) as is_tokens_launched
    FROM
        distinct_warpcast_followers wf
        LEFT JOIN k3l_rank on (wf.fid = k3l_rank.profile_id and k3l_rank.strategy_id = 9)
        LEFT JOIN k3l_channel_rank klcr
            on (wf.fid = klcr.fid and wf.channel_id = klcr.channel_id and klcr.strategy_name = $2)
        LEFT JOIN warpcast_members on (warpcast_members.fid = wf.fid and warpcast_members.channel_id = wf.channel_id)
        LEFT JOIN k3l_channel_points_bal as bal
            on (bal.channel_id=wf.channel_id and bal.fid=wf.fid)
        LEFT JOIN k3l_channel_tokens_bal as tok
            on (tok.channel_id=wf.channel_id and tok.fid=wf.fid)
      	LEFT JOIN k3l_channel_rewards_config as config
                on (config.channel_id = wf.channel_id)
      	LEFT JOIN k3l_channel_points_log as plog
      			on (plog.model_name='cbrt_weighted' AND plog.channel_id=wf.channel_id
                AND plog.fid = wf.fid
                AND plog.insert_ts > now() - interval '8 days')
    ),
    bio_data AS (
        SELECT
            followers_data.fid,
            any_value(profiles.username) as username,
            any_value(profiles.pfp_url) as pfp,
            any_value(profiles.bio) as bio,
            ARRAY_AGG(DISTINCT v.claim->>'address') as address
        FROM followers_data
        LEFT JOIN neynarv3.profiles on (profiles.fid = followers_data.fid)
        LEFT JOIN verifications v on (v.fid = followers_data.fid and v.deleted_at is null)
        GROUP BY followers_data.fid
      )
    SELECT
        followers_data.fid,
        any_value(username) as username,
        any_value(pfp) as pfp,
        any_value(bio) as bio,
        channel_id,
        channel_rank as rank,
        max(channel_score) as score,
        global_rank,
        any_value(address) as addresses,
        max(balance) as balance,
        max(token_balance) as token_balance,
        max(daily_earnings) as daily_earnings,
        max(token_daily_earnings) as token_daily_earnings,
        bool_and(is_weekly_earnings_available) as is_weekly_earnings_available,
        sum(latest_earnings) as latest_earnings,
        max(token_latest_earnings) as token_latest_earnings,
        sum(weekly_earnings) as weekly_earnings,
        max(token_weekly_earnings) as token_weekly_earnings,
        max(bal_update_ts) as bal_update_ts,
        bool_or(is_points_launched) as is_points_launched,
        bool_or(is_tokens_launched) as is_tokens_launched,
        min(memberat) as memberat
    FROM followers_data
    LEFT JOIN bio_data ON (bio_data.fid=followers_data.fid)
    GROUP BY followers_data.fid,channel_id,channel_rank,global_rank
    ORDER BY channel_rank,global_rank NULLS LAST
    OFFSET $3
    LIMIT $4
    """

    return await fetch_rows(
        channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool
    )


async def get_top_channel_holders(
    channel_id: str,
    strategy_name: str,
    orderby: ChannelEarningsOrderBy,
    offset: int,
    limit: int,
    pool: Pool,
):
    if orderby == ChannelEarningsOrderBy.WEEKLY:
        orderby_clause = "ORDER BY weekly_earnings DESC NULLS LAST, channel_rank,global_rank NULLS LAST"
    elif orderby == ChannelEarningsOrderBy.DAILY:
        orderby_clause = "ORDER BY daily_earnings DESC NULLS LAST, channel_rank, global_rank NULLS LAST"
    elif orderby == ChannelEarningsOrderBy.LATEST:
        orderby_clause = "ORDER BY latest_earnings DESC NULLS LAST, channel_rank, global_rank NULLS LAST"
    elif orderby == ChannelEarningsOrderBy.TOTAL:
        orderby_clause = (
            "ORDER BY balance DESC NULLS LAST, channel_rank,global_rank NULLS LAST"
        )
    else:
        orderby_clause = "ORDER BY channel_rank,global_rank NULLS LAST"

    # CLOSEST_SUNDAY = 'now()::DATE - EXTRACT(DOW FROM now())::INTEGER'
    monday_utc_timestamp = _dow_utc_timestamp_str(DOW.MONDAY)
    tuesday_utc_timestamp = _dow_utc_timestamp_str(DOW.TUESDAY)
    last_tuesday_utc_timestamp = _last_dow_utc_timestamp_str(DOW.TUESDAY)

    sql_query = f"""
    WITH
    total_balances as (
        SELECT
            count(*) as num_holders
        FROM
            k3l_channel_points_bal
        WHERE
            channel_id = $1
    ),
    balance_data as (
        SELECT
            bal.fid,
            bal.channel_id,
            klcr.rank as channel_rank,
            klcr.score as channel_score,
            k3l_rank.rank as global_rank,
            warpcast_members.memberat,
            warpcast_followers.followedat,
            bal.balance as balance,
            tok.balance as token_balance,
            CASE
                WHEN (plog.insert_ts < now() - interval '1 days') THEN 0
                WHEN (bal.insert_ts = bal.update_ts) THEN 0 -- airdrop
                ELSE plog.earnings
            END as daily_earnings,
            0 as token_daily_earnings,
            CASE
                WHEN (now() BETWEEN {monday_utc_timestamp} AND {tuesday_utc_timestamp}) THEN false
                ELSE true
            END as is_weekly_earnings_available,
            CASE
                WHEN (
                    now() BETWEEN {monday_utc_timestamp} AND {tuesday_utc_timestamp}
                    AND plog.insert_ts > {last_tuesday_utc_timestamp}
                    AND plog.insert_ts < {tuesday_utc_timestamp}
                ) THEN plog.earnings
            END as latest_earnings,
            tok.latest_earnings as token_latest_earnings,
            CASE
                WHEN (
                        (now() > {monday_utc_timestamp} AND plog.insert_ts > {tuesday_utc_timestamp})
                        OR
                        (now() < {monday_utc_timestamp} AND plog.insert_ts > {last_tuesday_utc_timestamp})
                    ) THEN plog.earnings
                ELSE 0
            END as weekly_earnings,
            0 as token_weekly_earnings,
            bal.update_ts as bal_update_ts,
            true as is_points_launched,
            coalesce(config.is_tokens, false) as is_tokens_launched,
            plog.boost AS boost
        FROM
            k3l_channel_points_bal as bal
            LEFT JOIN k3l_rank on (bal.fid = k3l_rank.profile_id and k3l_rank.strategy_id = 9)
            LEFT JOIN k3l_channel_rank klcr
                on (bal.fid = klcr.fid and bal.channel_id = klcr.channel_id and klcr.strategy_name = $2)
            LEFT JOIN warpcast_members on (warpcast_members.fid = bal.fid and warpcast_members.channel_id = bal.channel_id)
            LEFT JOIN warpcast_followers on (warpcast_followers.fid = bal.fid and warpcast_followers.channel_id = bal.channel_id)
            LEFT JOIN k3l_channel_tokens_bal as tok
                on (tok.channel_id=bal.channel_id and tok.fid=bal.fid)
            LEFT JOIN k3l_channel_rewards_config as config
                    on (config.channel_id = bal.channel_id)
            LEFT JOIN k3l_channel_points_log as plog
                    on (plog.model_name='cbrt_weighted' AND plog.channel_id=bal.channel_id
                    AND plog.fid = bal.fid
                    AND plog.insert_ts > now() - interval '8 days')
        WHERE bal.channel_id = $1
    ),
    bio_data AS (
        SELECT
            balance_data.fid,
            any_value(profiles.username) as username,
            any_value(profiles.pfp_url) as pfp,
            any_value(profiles.bio) as bio,
            ARRAY_AGG(DISTINCT v.claim->>'address') as address,
            min(profiles.created_at) as approx_fid_origints
        FROM balance_data
        LEFT JOIN neynarv3.profiles on (profiles.fid = balance_data.fid)
        LEFT JOIN verifications v on (v.fid = balance_data.fid AND v.deleted_at IS NULL)
        GROUP BY balance_data.fid
    ),
    leaderboard AS (
        SELECT
            balance_data.fid,
            any_value(username) as username,
            any_value(pfp) as pfp,
            any_value(bio) as bio,
            channel_id,
            channel_rank as rank,
            max(channel_score) as score,
            global_rank,
            any_value(address) as addresses,
            max(balance) as balance,
            max(token_balance) as token_balance,
            max(daily_earnings) as daily_earnings,
            max(token_daily_earnings) as token_daily_earnings,
            bool_and(is_weekly_earnings_available) as is_weekly_earnings_available,
            sum(latest_earnings) as latest_earnings,
            max(token_latest_earnings) as token_latest_earnings,
            sum(weekly_earnings) as weekly_earnings,
            max(token_weekly_earnings) as token_weekly_earnings,
            max(bal_update_ts) as bal_update_ts,
            COALESCE(max(boost), 1) > 1 AS boosted,
            bool_or(is_points_launched) as is_points_launched,
            bool_or(is_tokens_launched) as is_tokens_launched,
            min(memberat) as memberat,
            min(followedat) as followedat,
            EXTRACT(EPOCH FROM (min(approx_fid_origints))) as approx_fid_originat
        FROM balance_data
        LEFT JOIN bio_data ON (bio_data.fid=balance_data.fid)
        GROUP BY balance_data.fid,channel_id,channel_rank,global_rank
        {orderby_clause}
    )
    SELECT
        100-((total_balances.num_holders - (row_number() over()))*100 / total_balances.num_holders) as top_ptile,
        leaderboard.*
    FROM leaderboard, total_balances
    OFFSET $3
    LIMIT $4
    """

    return await fetch_rows(
        channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool
    )


async def get_top_channel_repliers(
    channel_id: str, strategy_name: str, offset: int, limit: int, pool: Pool
):
    sql_query = f"""
        WITH
        non_member_followers as (
          SELECT
              distinct wf.fid,
              wf.channel_id,
              ch.url as channel_url
          FROM warpcast_followers as wf
          LEFT JOIN warpcast_members as wm
            ON (wm.fid = wf.fid
                AND wm.channel_id = wf.channel_id
                {
        "AND wm.insert_ts=(select max(insert_ts) FROM warpcast_members where channel_id=$1)"
        if settings.DB_VERSION == DBVersion.EIGEN2
        else ""
    }
               )
          INNER JOIN warpcast_channels_data as ch on (wf.channel_id = ch.id and ch.id=$1)
          WHERE
          wm.fid IS NULL
          {
        "AND wf.insert_ts=(select max(insert_ts) FROM warpcast_followers where channel_id=$1)"
        if settings.DB_VERSION == DBVersion.EIGEN2
        else ""
    }
        ),
        followers_data as (
            SELECT
                nmf.fid,
                nmf.channel_id,
                '0x' || encode(casts.hash, 'hex') as cast_hash,
                klcr.rank as channel_rank,
                k3l_rank.rank as global_rank,
                profiles.username AS username,
                profiles.pfp_url pfp
            FROM
                non_member_followers as nmf
                INNER JOIN neynarv3.casts
                    ON (casts.fid = nmf.fid
                        AND casts.root_parent_url = nmf.channel_url
                        AND casts.parent_hash IS NOT NULL
                        AND casts.deleted_at IS NULL
                        AND casts.timestamp
                              BETWEEN now() - interval '1 days'
                                  AND now()
                    )
                LEFT JOIN k3l_rank on (nmf.fid = k3l_rank.profile_id  and k3l_rank.strategy_id = 9)
                LEFT JOIN k3l_channel_rank klcr
                    on (nmf.fid = klcr.fid and nmf.channel_id  = klcr.channel_id and klcr.strategy_name = $2)
                LEFT JOIN neynarv3.profiles on (profiles.fid = nmf.fid)
        )
        SELECT
            fid,
            channel_id,
            channel_rank,
            global_rank,
            (array_agg(distinct(cast_hash)))[1:1] as cast_hash,
            any_value(username) as username,
            any_value(pfp) as pfp
        FROM followers_data
        GROUP BY fid,channel_id,channel_rank,global_rank
        ORDER BY channel_rank,global_rank NULLS LAST
        OFFSET $3
        limit $4

    """

    return await fetch_rows(
        channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool
    )


# TODO deprecate in favor of get_trending_channel_casts_lite
async def get_trending_channel_casts_heavy(
    channel_id: str,
    channel_url: str,
    channel_strategy: str,
    max_cast_age: str,
    agg: ScoreAgg,
    score_threshold: float,
    reactions_threshold: int,
    cutoff_ptile: int,
    weights: Weights,
    shuffle: bool,
    time_decay: CastsTimeDecay,
    normalize: bool,
    offset: int,
    limit: int,
    sorting_order: SortingOrder,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    decay_sql = sql_for_decay("CURRENT_TIMESTAMP - ci.action_ts", time_decay)

    if normalize:
        fid_score_sql = "cbrt(fids.score)"
    else:
        fid_score_sql = "fids.score"

    if shuffle:
        shuffle_sql = "random(),"
    else:
        shuffle_sql = ""

    order_sql = "cast_score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_sql = "cast_score DESC"
        case SortingOrder.RECENT:
            order_sql = "cast_ts DESC"
        case SortingOrder.HOUR:
            order_sql = f"age_hours ASC, {shuffle_sql} cast_score DESC"
        case SortingOrder.DAY:
            order_sql = f"age_days ASC, {shuffle_sql} cast_score DESC"
        case SortingOrder.REACTIONS:
            order_sql = f"reaction_count DESC, {shuffle_sql} cast_score DESC"

    sql_query = f"""
    WITH
    fid_cast_scores as (
        SELECT
            hash as cast_hash,
            SUM(
                (
                    ({weights.cast} * {fid_score_sql} * ci.casted)
                    + ({weights.reply} * {fid_score_sql} * ci.replied)
                    + ({weights.recast} * {fid_score_sql} * ci.recasted)
                    + ({weights.like} * {fid_score_sql} * ci.liked)
                )
                *
                {decay_sql}
            ) as cast_score,
            ci.fid,
            MIN(casts.timestamp) as cast_ts
        FROM k3l_recent_parent_casts as casts
        INNER JOIN k3l_cast_action as ci
            ON (ci.cast_hash = casts.hash
                AND ci.action_ts > now() - interval '{max_cast_age}'
                AND casts.root_parent_url = $2)
        INNER JOIN k3l_channel_rank as fids ON (fids.channel_id=$1 AND fids.fid = ci.fid and fids.strategy_name = $3)
        LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
        LEFT JOIN cura_hidden_fids as hids ON (hids.hidden_fid=ci.fid AND hids.channel_id=$1)
        WHERE md.affected_userid IS NULL AND hids.hidden_fid IS NULL
        AND casts.timestamp > now() - interval '{max_cast_age}'
        GROUP BY casts.hash, ci.fid
        ORDER BY cast_ts DESC
    ),
    scores AS (
        SELECT
            cast_hash,
            {agg_sql} as cast_score,
            MIN(cast_ts) as cast_ts,
            COUNT (*) - 1 as reaction_count
        FROM fid_cast_scores
        GROUP BY cast_hash
    ),
    cast_details AS (
        SELECT
            '0x' || encode(scores.cast_hash, 'hex') as cast_hash,
            FLOOR(EXTRACT(EPOCH FROM (now() - ci.timestamp))/3600) as age_hours,
            FLOOR(EXTRACT(EPOCH FROM (now() - ci.timestamp))/(60 * 60 * 24)::numeric) AS age_days,
            ci.timestamp as cast_ts,
            scores.cast_score,
            scores.reaction_count as reaction_count,
            ci.text,
            ci.fid,
            fids.channel_id,
            fids.rank AS channel_rank,
            k3l_rank.rank AS global_rank,
            NTILE(100) OVER (ORDER BY cast_score DESC) as ptile
        FROM scores
        INNER JOIN k3l_recent_parent_casts AS ci ON ci.hash = scores.cast_hash
        INNER JOIN k3l_rank ON (ci.fid = k3l_rank.profile_id and k3l_rank.strategy_id=9)
        INNER JOIN k3l_channel_rank AS fids ON (ci.fid = fids.fid AND fids.channel_id = $1 AND fids.strategy_name = $3)
        WHERE
            ci.timestamp > now() - interval '{max_cast_age}'
            AND scores.cast_score >= {score_threshold}
            AND scores.reaction_count >= {reactions_threshold}
    ),
    feed AS (
        SELECT
            distinct
            cast_details.cast_hash,
            ANY_VALUE(cast_details.fid) as fid,
            ANY_VALUE(cast_details.channel_id) as channel_id,
            MIN(cast_details.channel_rank) as channel_rank,
            MIN(cast_details.global_rank) as global_rank,
            MIN(cast_details.ptile) as ptile,
            ANY_VALUE(profiles.username) as username,
            ANY_VALUE(profiles.pfp_url) as pfp,
            ANY_VALUE(profiles.bio) as bio,
            MAX(cast_details.cast_score) as cast_score,
            MAX(cast_details.reaction_count) as reaction_count,
            MIN(cast_details.age_hours) as age_hours,
            MIN(cast_details.age_days) as age_days,
            MIN(cast_details.cast_ts) as cast_ts,
            ANY_VALUE(cast_details.text) as text
        FROM cast_details
        LEFT JOIN neynarv3.profiles ON (cast_details.fid = profiles.fid)
        GROUP BY cast_details.cast_hash
    )
    SELECT * FROM feed
    WHERE ptile <= {cutoff_ptile}
    ORDER BY {order_sql}
    OFFSET $4
    LIMIT $5
    """

    return await fetch_rows(
        channel_id,
        channel_url,
        channel_strategy,
        offset,
        limit,
        sql_query=sql_query,
        pool=pool,
    )


@memoize(
    configuration=MutableCacheConfiguration.initialized_with(
        DefaultInMemoryCacheConfiguration()
    ).set_key_extractor(
        EncodedMethodNameAndArgsExcludedKeyExtractor(
            skip_first_arg_as_self=False, skip_args=[15], skip_kwargs=["pool"]
        )
    )
)
async def get_trending_channel_casts_lite_memoized(
    channel_id: str,
    channel_url: str,
    channel_strategy: str,
    max_cast_age: str,
    agg: ScoreAgg,
    score_threshold: float,
    reactions_threshold: int,
    cutoff_ptile: int,
    weights: Weights,
    shuffle: bool,
    time_decay: CastsTimeDecay,
    normalize: bool,
    offset: int,
    limit: int,
    sorting_order: SortingOrder,
    pool: Pool,
):
    # You can use 'extra_arg' here if needed
    return await get_trending_channel_casts_lite(
        channel_id=channel_id,
        channel_url=channel_url,
        channel_strategy=channel_strategy,
        max_cast_age=max_cast_age,
        agg=agg,
        score_threshold=score_threshold,
        reactions_threshold=reactions_threshold,
        cutoff_ptile=cutoff_ptile,
        weights=weights,
        shuffle=shuffle,
        time_decay=time_decay,
        normalize=normalize,
        offset=offset,
        limit=limit,
        sorting_order=sorting_order,
        pool=pool,
    )


async def get_trending_channel_casts_lite(
    channel_id: str,
    channel_url: str,
    channel_strategy: str,
    max_cast_age: str,
    agg: ScoreAgg,
    score_threshold: float,
    reactions_threshold: int,
    cutoff_ptile: int,
    weights: Weights,
    shuffle: bool,
    time_decay: CastsTimeDecay,
    normalize: bool,
    offset: int,
    limit: int,
    sorting_order: SortingOrder,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    decay_sql = sql_for_decay("CURRENT_TIMESTAMP - ci.action_ts", time_decay)

    if normalize:
        fid_score_sql = "cbrt(fids.score)"
    else:
        fid_score_sql = "fids.score"

    if shuffle:
        shuffle_sql = "random(),"
    else:
        shuffle_sql = ""

    order_sql = "cast_score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_sql = "cast_score DESC"
        case SortingOrder.RECENT:
            order_sql = "cast_ts DESC"
        case SortingOrder.HOUR:
            order_sql = f"age_hours ASC, {shuffle_sql} cast_score DESC"
        case SortingOrder.DAY:
            order_sql = f"age_days ASC, {shuffle_sql} cast_score DESC"
        case SortingOrder.REACTIONS:
            order_sql = "reaction_count DESC, cast_score DESC"

    sql_query = f"""
    WITH
    fid_cast_scores as (
        SELECT
            hash as cast_hash,
            SUM(
                (
                    ({weights.cast} * {fid_score_sql} * ci.casted)
                    + ({weights.reply} * {fid_score_sql} * ci.replied)
                    + ({weights.recast} * {fid_score_sql} * ci.recasted)
                    + ({weights.like} * {fid_score_sql} * ci.liked)
                )
                *
                {decay_sql}
            ) as cast_score,
                        ci.fid,
            MIN(casts.timestamp) as cast_ts
        FROM k3l_recent_parent_casts as casts
        INNER JOIN k3l_cast_action as ci
            ON (ci.cast_hash = casts.hash
                AND ci.action_ts > now() - interval '{max_cast_age}'
                AND casts.root_parent_url = $2)
        INNER JOIN k3l_channel_rank as fids ON (fids.channel_id=$1 AND fids.fid = ci.fid and fids.strategy_name = $3)
        LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
        LEFT JOIN cura_hidden_fids as hids ON (hids.hidden_fid=ci.fid AND hids.channel_id=$1)
        WHERE md.affected_userid IS NULL AND hids.hidden_fid IS NULL
        AND casts.timestamp > now() - interval '{max_cast_age}'
        GROUP BY casts.hash, ci.fid
        ORDER BY cast_ts DESC
    ),
    scores AS (
        SELECT
            cast_hash,
            {agg_sql} as cast_score,
            MIN(cast_ts) as cast_ts,
            COUNT (*) - 1 as reaction_count
        FROM fid_cast_scores
        GROUP BY cast_hash
    ),
    cast_scores AS (
        SELECT
            '0x' || encode(cast_hash, 'hex') as cast_hash,
            FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/3600) as age_hours,
            FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/(60 * 60 * 24)::numeric) AS age_days,
            cast_ts,
            cast_score,
            NTILE(100) OVER (ORDER BY cast_score DESC) as ptile
        FROM scores
        WHERE
            cast_score >= {score_threshold}
            AND reaction_count >= {reactions_threshold}
    )
    SELECT
        *
    FROM cast_scores
    WHERE ptile <= {cutoff_ptile}
    ORDER BY {order_sql}
    OFFSET $4
    LIMIT $5
    """

    return await fetch_rows(
        channel_id,
        channel_url,
        channel_strategy,
        offset,
        limit,
        sql_query=sql_query,
        pool=pool,
    )


async def get_channel_casts_scores_lite(
    cast_hashes: list[bytes],
    channel_id: str,
    channel_strategy: str,
    agg: ScoreAgg,
    score_threshold: float,
    weights: Weights,
    time_decay: CastsTimeDecay,
    normalize: bool,
    sorting_order: SortingOrder,
    pool: Pool,
):
    agg_sql = sql_for_agg(agg, "fid_cast_scores.cast_score")

    decay_sql = sql_for_decay("CURRENT_TIMESTAMP - ci.action_ts", time_decay)

    if normalize:
        fid_score_sql = "cbrt(fids.score)"
    else:
        fid_score_sql = "fids.score"

    order_sql = "cast_score DESC"
    match sorting_order:
        case SortingOrder.SCORE | SortingOrder.POPULAR:
            order_sql = "cast_score DESC"
        case SortingOrder.RECENT:
            order_sql = "cast_ts DESC"
        case SortingOrder.HOUR:
            order_sql = "age_hours ASC, cast_score DESC"
        case SortingOrder.DAY:
            order_sql = "age_days ASC, cast_score DESC"
        case SortingOrder.REACTIONS:
            order_sql = "reaction_count DESC, cast_score DESC"

    sql_query = f"""
    WITH
    fid_cast_scores as (
        SELECT
            ci.cast_hash,
            SUM(
                (
                    ({weights.cast} * {fid_score_sql} * ci.casted)
                    + ({weights.reply} * {fid_score_sql} * ci.replied)
                    + ({weights.recast} * {fid_score_sql} * ci.recasted)
                    + ({weights.like} * {fid_score_sql} * ci.liked)
                )
                *
                {decay_sql}
            ) as cast_score,
            ci.fid,
            MIN(ci.action_ts) as cast_ts
        FROM k3l_cast_action as ci
        INNER JOIN k3l_channel_rank as fids
            ON (fids.channel_id = $1
                AND fids.fid = ci.fid
                AND fids.strategy_name = $2
                AND ci.cast_hash = ANY($3::bytea[])
             )
        LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
        WHERE md.channel_id IS NULL
        GROUP BY ci.cast_hash, ci.fid
        ORDER BY cast_ts DESC
    ),
    scores AS (
        SELECT
            cast_hash,
            {agg_sql} as cast_score,
            MIN(cast_ts) as cast_ts,
            COUNT (*) - 1 as reaction_count
        FROM fid_cast_scores
        GROUP BY cast_hash
    )
    SELECT
        '0x' || encode(cast_hash, 'hex') as cast_hash,
        FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/3600) as age_hours,
        FLOOR(EXTRACT(EPOCH FROM (now() - cast_ts))/(60 * 60 * 24)::numeric) AS age_days,
        cast_ts,
        cast_score
    FROM scores
    WHERE cast_score >= {score_threshold}
    ORDER BY {order_sql}
    """

    return await fetch_rows(
        channel_id, channel_strategy, cast_hashes, sql_query=sql_query, pool=pool
    )


async def get_trending_channels(
    max_cast_age: str, rank_threshold: int, offset: int, limit: int, pool: Pool
):
    sql_query = f"""
    WITH top_fids AS (
        SELECT
            profile_id as fid, rank
        FROM
            k3l_rank
        WHERE strategy_id=9 AND rank <= $1
        ORDER BY rank
    ),
    top_channels AS (
        SELECT
            casts.root_parent_url as url,
            count(*) as score
        FROM k3l_recent_parent_casts AS casts
        INNER JOIN top_fids ON (top_fids.fid = casts.fid
            AND casts.timestamp > now() - interval '{max_cast_age}'
            AND casts.root_parent_url IS NOT NULL)
        GROUP BY casts.root_parent_url
    )
    SELECT
        ch.id,
        top_channels.score
        {", ch.pinnedcasthash" if settings.DB_VERSION == DBVersion.EIGEN2 else ""}
    FROM top_channels
    INNER JOIN warpcast_channels_data as ch ON (ch.url = top_channels.url)
    ORDER BY top_channels.score DESC
    OFFSET $2
    LIMIT $3
    """

    return await fetch_rows(
        rank_threshold, offset, limit, sql_query=sql_query, pool=pool
    )


async def score_casts(
    hashes: list[bytes],
    weights: Weights,
    time_decay_base: float,
    time_decay_period: timedelta,
    pool: Pool,
) -> list[CastScore]:
    decay_sql = sql_for_decay(
        "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - action_ts",
        period=time_decay_period,
        base=time_decay_base,
    )
    query = f"""
    WITH ca AS (
        SELECT
            cast_hash AS hash,
            fid,
            (
                liked * $2 +
                casted * $3 +
                recasted * $4 +
                replied * $5
            ) * {decay_sql} AS weight
        FROM k3l_cast_action
        WHERE cast_hash = ANY($1::bytea[])
    )
    SELECT
        ca.hash,
        sum(ca.weight * r.score) AS score
    FROM ca
    JOIN k3l_rank r ON ca.fid = r.profile_id AND r.strategy_id = 9
    GROUP BY ca.hash
    """
    rows = await fetch_rows(
        hashes,
        weights.like,
        weights.cast,
        weights.recast,
        weights.reply,
        sql_query=query,
        pool=pool,
    )
    return [CastScore(**row) for row in rows]


async def get_channel_config(channel_id: str, pool: Pool):
    """Get channel configuration from k3l_channel_rewards_config table."""
    sql_query = """
        SELECT 
            is_ranked,
            is_points,
            is_tokens
        FROM k3l_channel_rewards_config
        WHERE channel_id = $1
    """
    rows = await fetch_rows(channel_id, sql_query=sql_query, pool=pool)
    if rows:
        return rows[0]
    return None


async def get_top_channel_casts(
    channel_id: str,
    cast_at_or_after: datetime,
    cast_before: datetime,
    reaction_window: timedelta,
    weights: Weights,
    strategy_name: str,
    pool: Pool,
):
    # Ensure that timestamps are zone-aware.
    if cast_at_or_after.tzinfo is None:
        cast_at_or_after = cast_at_or_after.astimezone()
    if cast_before.tzinfo is None:
        cast_before = cast_before.astimezone()
    return await fetch_rows(
        channel_id,  # $1
        cast_at_or_after.astimezone(UTC).replace(tzinfo=None),
        cast_before.astimezone(UTC).replace(tzinfo=None),
        reaction_window,
        weights.like,
        weights.cast,
        weights.recast,
        weights.reply,
        strategy_name,
        sql_query=f"""
            WITH ca AS (
                SELECT ca.*
                FROM neynarv3.casts AS c
                INNER JOIN
                    k3l_cast_action AS ca
                    ON
                        c.hash = ca.cast_hash
                        AND c.timestamp <= ca.action_ts
                        AND ca.action_ts < c.timestamp + $4::interval
                WHERE
                    c.root_parent_url = (
                        SELECT url
                        FROM neynarv3.channels
                        WHERE channel_id = $1::text
                    )
                    AND c.parent_hash IS NULL
                    AND c.timestamp >= $2::timestamp
                    AND c.timestamp < $3::timestamp
            ),
            
            c AS (
                SELECT
                    ca.cast_hash,
                    sum(
                        (
                            ca.liked * $5::integer
                            + ca.casted * $6::integer
                            + ca.recasted * $7::integer
                            + ca.replied * $8::integer
                        )
                        * cbrt(cr.score)
                    ) AS score
                FROM ca
                INNER JOIN k3l_channel_rank AS cr ON ca.fid = cr.fid
                WHERE
                    cr.strategy_name = $9::text
                    AND cr.channel_id = $1::text
                GROUP BY ca.cast_hash
            )
            
            SELECT
                score,
                '0x' || encode(cast_hash, 'hex') AS cast_hash
            FROM c
            ORDER BY score DESC
        """,
        pool=pool,
    )


class BelieverLeaderboardRow(BaseModel):
    order_rank: int
    fid: int
    pfp: str
    username: str
    score: int
    cast_hashes: list[str]


@cache.early(ttl=settings.CACHE_TTL, early_ttl=settings.CACHE_EARLY_TTL)
async def get_believer_leaderboard(
    *,
    chain_id: int,
    token_address: ChecksumAddress,
    tx_only: bool,
    start_time: datetime,
    end_time: datetime,
    global_trust_strategy_id: int,
    weights: Weights,
    pool: Pool,
) -> list[BelieverLeaderboardRow]:
    """
    Fetches a trader leaderboard based on various parameters and criteria.

    This function queries a database to generate a ranked leaderboard of traders
    for a given ERC-20 token contract, over a specified time period, and according
    to the provided trust strategy weights. It calculates points for each trader
    based on their activities and normalizes the values accordingly.

    :param chain_id: The blockchain chain ID to identify the relevant network.
    :param token_address: The address of the ERC-20 token for which
        the leaderboard is being generated.
    :param tx_only: Whether to consider only casts with embedded TX URL.
    :param start_time: The start of the time range for evaluating activity.
        The date must be timezone-aware or UTC-naive.
    :param end_time: The end of the time range for evaluating activity.
        The date must be timezone-aware or UTC-naive.
    :param global_trust_strategy_id: The ID of the global trust strategy to use
        for calculating trader scores.
    :param weights: A Weights object containing weight factors for specific
        trader actions such as casts, likes, etc.
    :param pool: A database connection pool used for executing queries.

    :returns: A list of dictionaries where each dictionary represents a trader
        and contains their ID (`fid`), leaderboard points, and associated hashes of their
        casts.

    :raises `ValueError`: If `end_time` is less than or equal to `start_time`.
    """
    if start_time.tzinfo is not None:
        start_time = start_time.astimezone(UTC).replace(tzinfo=None)
    if end_time.tzinfo is not None:
        end_time = end_time.astimezone(UTC).replace(tzinfo=None)
    if end_time <= start_time:
        raise ValueError("end_time must be greater than start_time")
    num_days = (end_time - start_time).total_seconds() / 86400
    budget = num_days * 10000
    sql, args = pyformat2dollar(
        """
            WITH
            casts AS (
                SELECT hash, fid
                FROM neynarv3.casts
                WHERE
                    is_eip155_erc20_url(parent_url)
                    AND eip155_chain(parent_url) = %(chain_id)s::bigint
                    AND eip155_erc20_token(parent_url) = %(token_address)s::bytea
                    AND CASE WHEN %(tx_only)s::bool THEN (embeds_eip155_tx_hashes(embeds, %(chain_id)s::bigint))[1] IS NOT NULL ELSE TRUE END
                    AND parent_hash IS NULL
            ),
            actions AS (
                SELECT *
                FROM k3l_cast_action
                WHERE
                    action_ts >= %(start_time)s
                    AND action_ts < %(end_time)s
            ),
            raw AS (
                SELECT
                    c.fid,
                    sum(
                        (
                            a.casted * %(cast_weight)s +
                            a.liked * %(like_weight)s +
                            a.recasted * %(recast_weight)s +
                            a.replied * %(reply_weight)s
                        ) * gt.score
                    ) AS value,
                    array_agg(DISTINCT '0x' || encode(c.hash, 'hex')) AS cast_hashes
                FROM casts c
                JOIN actions a ON c.hash = a.cast_hash
                JOIN k3l_rank gt ON a.fid = gt.profile_id AND gt.strategy_id = %(global_trust_strategy_id)s
                GROUP BY c.fid
            ),
            normalized AS (
                SELECT
                    fid,
                    cbrt(value) AS value
                FROM raw
                WHERE value > 0
            ),
            leaderboard AS (
                SELECT
                    fid,
                    round(%(budget)s * value / (SELECT sum(value) FROM normalized))::bigint AS points
                FROM normalized
            )
        SELECT
            rank() OVER (ORDER BY points DESC) AS order_rank,
            fid,
            p.pfp_url AS pfp,
            p.username AS username,
            lb.points AS score,
            raw.cast_hashes
        FROM leaderboard lb
        JOIN raw USING (fid)
        JOIN neynarv3.profiles p USING (fid)
        WHERE points > 0
        ORDER BY points DESC;
        """,
        chain_id=chain_id,
        token_address=to_bytes(hexstr=token_address),
        tx_only=tx_only,
        start_time=start_time,
        end_time=end_time,
        global_trust_strategy_id=global_trust_strategy_id,
        cast_weight=weights.cast,
        like_weight=weights.like,
        recast_weight=weights.recast,
        reply_weight=weights.reply,
        budget=budget,
    )
    return [
        BelieverLeaderboardRow(**row)
        for row in await fetch_rows(*args, sql_query=sql, pool=pool)
    ]


async def get_trending_fip2(
    *,
    start_time: datetime,
    end_time: datetime,
    decay_rate: float,
    chain_id: int,
    tx_only: bool,
    offset: int,
    limit: int,
    weights: Weights,
    pool: Pool,
):
    if start_time.tzinfo is not None:
        start_time = start_time.astimezone(UTC).replace(tzinfo=None)
    if end_time.tzinfo is not None:
        end_time = end_time.astimezone(UTC).replace(tzinfo=None)
    sql, args = pyformat2dollar(
        """
            WITH
            c AS (
                SELECT hash, fid, timestamp, eip155_erc20_token(parent_url) AS token
                FROM neynarv3.casts
                WHERE
                    is_eip155_erc20_url(parent_url)
                    AND eip155_chain(parent_url) = %(chain_id)s::bigint
                    AND CASE WHEN %(tx_only)s::bool THEN (embeds_eip155_tx_hashes(embeds, %(chain_id)s::bigint))[1] IS NOT NULL ELSE TRUE END
                    AND parent_hash IS NULL
                    AND deleted_at IS NULL
            ),
            raw AS (
                SELECT
                    '0x' || encode(token, 'hex') AS token,
                    sum(
                        %(decay_rate)s ^ (EXTRACT(EPOCH FROM (%(end_time)s - c."timestamp")) / 86400) *
                        (
                            ca.liked * %(like_weight)s +
                            ca.casted * %(cast_weight)s +
                            ca.recasted * %(recast_weight)s +
                            ca.replied * %(reply_weight)s
                        ) *
                        r.score
                    ) AS score,
                    count(DISTINCT c.hash) AS num_casts,
                    count(*) FILTER (WHERE ca.liked + ca.recasted + ca.replied > 0) AS num_reactions
                FROM c
                JOIN k3l_cast_action ca ON c.hash = ca.cast_hash
                JOIN k3l_rank r ON ca.fid = r.profile_id
                WHERE
                    COALESCE(ca.action_ts >= %(start_time)s, TRUE)
                    AND ca.action_ts < %(end_time)s
                GROUP BY c.token
            )
            SELECT *
            FROM raw
            ORDER BY score DESC
            OFFSET %(offset)s
            LIMIT %(limit)s;
        """,
        start_time=start_time,
        end_time=end_time,
        like_weight=weights.like,
        cast_weight=weights.cast,
        recast_weight=weights.recast,
        reply_weight=weights.reply,
        decay_rate=decay_rate,
        chain_id=chain_id,
        tx_only=tx_only,
        offset=offset,
        limit=limit,
    )
    return await fetch_rows(*args, sql_query=sql, pool=pool)


def pyformat2dollar(sql: str, *poargs: Any, **kwargs: Any) -> tuple[str, list[Any]]:
    """
    Formats a SQL query string containing Python-style parameter placeholders into an
    equivalent SQL string with dollar-style placeholders and a list of corresponding
    parameter values.

    :param sql: SQL query string with Python-style (%s) placeholders.
    :param poargs: Positional arguments for the parameters referenced in the SQL string.
    :param kwargs: Keyword arguments for the named parameters referenced in the SQL string.
    :return: A tuple containing the reformatted SQL string with dollar-style placeholders
        and the corresponding list of parameter values.

    >>> pyformat2dollar("SELECT %(name)s + %s", 3, name=5)
    ('SELECT $1 + $2', [5, 3])

    Interpolate keyword parameters as many times as necessary:

    >>> pyformat2dollar("SELECT %(name)s * %(name)s + %s", 3, name=5)
    ('SELECT $1 * $1 + $2', [5, 3])

    Raise `ValueError` if required arguments are not provided:

    >>> pyformat2dollar("SELECT %(name)s + %s + %s", 3, name=5)
    Traceback (most recent call last):
        ...
    ValueError: not enough positional arguments
    >>> pyformat2dollar("SELECT %(name)s + %(more)s + %(extra)s + %s", 3, name=5)
    Traceback (most recent call last):
        ...
    ValueError: missing keyword argument: 'more'

    Ignore extra positional/keyword arguments:

    >>> pyformat2dollar("SELECT %(name)s + %s", 3, 4, name=5)
    ('SELECT $1 + $2', [5, 3])
    >>> pyformat2dollar("SELECT %(name)s + %s", 3, name=5, extra=4)
    ('SELECT $1 + $2', [5, 3])

    Keep doubled (escaped) percent signs verbatim:

    >>> pyformat2dollar("SELECT 'needle' LIKE '%%haystack%%'")
    ("SELECT 'needle' LIKE '%%haystack%%'", [])

    Recognize only valid percent sequences (``%s``, ``%(name)s``, and ``%%``):

    >>> pyformat2dollar("SELECT 'needle' LIKE '%haystack%'")
    Traceback (most recent call last):
        ...
    ValueError: invalid % sequence '%h' in SQL at index 22
    """
    pct_re = re.compile(
        r"%(?:(?P<param>(?:\((?P<name>[A-Za-z_][A-Za-z0-9_]*)\))?s)|(?P<passthrough>%)|(?P<unknown>.))"
    )
    kwarg_indices: dict[str, int] = {}
    new_sql = ""
    new_args = []
    pos = 0
    for m in pct_re.finditer(sql):
        new_sql += sql[pos : m.start()]
        pos = m.end()
        if m.group("param") is not None:
            name = m.group("name")
            if name is None:
                try:
                    arg, poargs = poargs[0], poargs[1:]
                except IndexError:
                    raise ValueError("not enough positional arguments") from None
                new_args.append(arg)
                index = len(new_args)
            else:
                try:
                    arg = kwargs[name]
                except KeyError:
                    raise ValueError(f"missing keyword argument: {name!r}") from None
                try:
                    index = kwarg_indices[name]
                except KeyError:
                    new_args.append(arg)
                    index = len(new_args)
                    kwarg_indices[name] = index
            new_sql += f"${index}"
        elif m.group("passthrough") is not None:
            new_sql += m.group()
        elif (_unknown := m.group("unknown")) is not None:
            msg = f"invalid % sequence '%h' in SQL at index {m.start()}"
            raise ValueError(msg)
    new_sql += sql[pos:]
    return new_sql, new_args


def record2dict(record: asyncpg.Record) -> dict[str, Any]:
    return {key: value for key, value in record.items()}


def records2dicts(records: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [record2dict(record) for record in records]

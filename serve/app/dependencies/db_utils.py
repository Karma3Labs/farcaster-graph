import time
import json

from ..config import settings
from ..models.score_model import ScoreAgg, Weights, Voting
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from asyncpg.pool import Pool
from loguru import logger

engine = create_async_engine(
    settings.POSTGRES_ASYNC_URI.get_secret_value(),
    echo=settings.POSTGRES_ECHO,
    future=True,
    pool_size=max(5, settings.POSTGRES_POOL_SIZE),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


# async def get_db_session():
#     async with SessionLocal() as session:
#         try:
#             yield session
#         except Exception as e:
#             await session.rollback()
#             raise e
#         finally:
#             await session.close()

async def fetch_rows(
        *args,
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


async def get_handle_fid_for_addresses(
        addresses: list[str],
        pool: Pool
):
    sql_query = """
    (
        SELECT
            verifications.claim->>'address' as address,
            fnames.fname as fname,
            user_data.value as username,
            verifications.fid as fid
        FROM verifications
        LEFT JOIN fnames ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = verifications.fid and user_data.type=6)
        WHERE
            verifications.claim->>'address' = ANY($1::text[])
    UNION
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fids.fid as fid
        FROM fids
        LEFT JOIN fnames ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fids.fid and user_data.type=6)
            WHERE
                '0x' || encode(fids.custody_address, 'hex') = ANY($1::text[])
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(addresses, sql_query=sql_query, pool=pool)


async def get_all_fid_addresses_for_handles(
        handles: list[str],
        pool: Pool,
):
    sql_query = """
    (
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE
            (fnames.fname = ANY($1::text[]))
            OR
            (user_data.value = ANY($1::text[]))
    UNION
        SELECT
            verifications.claim->>'address' as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE
            (fnames.fname = ANY($1::text[]))
            OR
            (user_data.value = ANY($1::text[]))
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(handles, sql_query=sql_query, pool=pool)


async def get_unique_fid_metadata_for_handles(
        handles: list[str],
        pool: Pool,
):
    sql_query = """
    SELECT
        '0x' || encode(any_value(fids.custody_address), 'hex') as address,
        any_value(fnames.fname) as fname,
        any_value(user_data.value) as username,
        fids.fid as fid
    FROM fids
    INNER JOIN fnames ON (fids.fid = fnames.fid)
    LEFT JOIN user_data ON (user_data.fid = fids.fid and user_data.type=6)
    WHERE
        (fnames.fname = ANY($1::text[]))
        OR
        (user_data.value = ANY($1::text[]))
    GROUP BY fids.fid
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(handles, sql_query=sql_query, pool=pool)


async def get_all_handle_addresses_for_fids(
        fids: list[str],
        pool: Pool,
):
    sql_query = """
    WITH latest_global_rank as (
    select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=9
                and date in (select max(date) from k3l_rank)
    ),
    fid_details as
    (
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            fnames.fname as fname,
            case when user_data.type = 6 then user_data.value end as username,
            case when user_data.type = 1 then user_data.value end as pfp,
            case when user_data.type = 3 then user_data.value end as bio,
            fids.fid as fid
        FROM fids
        LEFT JOIN fnames ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fids.fid)
        WHERE
            fids.fid = ANY($1::integer[])
    UNION
        SELECT
            verifications.claim->>'address' as address,
            fnames.fname as fname,
            case when user_data.type = 6 then user_data.value end as username,
            case when user_data.type = 1 then user_data.value end as pfp,
            case when user_data.type = 3 then user_data.value end as bio,
            fids.fid as fid
        FROM fids
        INNER JOIN verifications ON (verifications.fid = fids.fid)
        LEFT JOIN fnames ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fids.fid)
        WHERE
            fids.fid = ANY($1::integer[])
    ),
    SELECT fid_details.*,
    latest_global_rank.global_rank
    FROM fid_details 
    LEFT JOIN latest_global_rank using(fid)
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)


async def get_unique_handle_metadata_for_fids(
        fids: list[str],
        pool: Pool,
):
    sql_query = """
    WITH 
    latest_global_rank as (
    select profile_id as fid, rank as global_rank, score from k3l_rank g where strategy_id=9
                and date in (select max(date) from k3l_rank)
    ),
    addresses AS (
    SELECT fid,'0x' || encode(fids.custody_address, 'hex') as address
    FROM fids where fid=ANY($1::integer[])
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
        ANY_VALUE(fnames.fname) as fname,
        ANY_VALUE(case when user_data.type = 6 then user_data.value end) as username,
        ANY_VALUE(case when user_data.type = 1 then user_data.value end)  as pfp,
        ANY_VALUE(case when user_data.type = 3 then user_data.value end) as bio 
        from agg_addresses
    LEFT JOIN fnames ON (agg_addresses.fid = fnames.fid)
    LEFT JOIN user_data ON (user_data.fid = agg_addresses.fid)
    LEFT JOIN latest_global_rank on (agg_addresses.fid = latest_global_rank.fid)
    GROUP BY agg_addresses.fid,agg_addresses.address,latest_global_rank.global_rank
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)


async def get_top_profiles(strategy_id: int, offset: int, limit: int, pool: Pool, query_type: str):
    if query_type == 'lite':
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
        )
        SELECT
            profile_id as fid,
            any_value(user_data.value) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
        WHERE strategy_id = $1
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        OFFSET $2
        LIMIT $3
        """
    elif query_type == 'superlite':
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
            any_value(fnames.fname) as fname,
            any_value(user_data.value) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN fnames on (fnames.fid = profile_id)
        LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
        WHERE strategy_id = $1
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        OFFSET $2
        LIMIT $3
        """
    return await fetch_rows(strategy_id, offset, limit, sql_query=sql_query, pool=pool)


async def get_top_channel_profiles(
        channel_id: str,
        strategy_name: str,
        offset: int,
        limit: int,
        lite: bool,
        pool: Pool
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
        ORDER BY rank ASC
        OFFSET $3
        LIMIT $4
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
        FROM fids
        UNION ALL
         SELECT v.claim->>'address' as address, fid
         FROM verifications v
        ),
        top_records as (
        SELECT
            ch.fid,
            fnames.fname as fname,
            case when user_data.type = 6 then user_data.value end as username,
            case when user_data.type = 1 then user_data.value end as pfp,
            case when user_data.type = 3 then user_data.value end as bio,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_channel_rank as ch
        CROSS JOIN total
        LEFT JOIN fnames on (fnames.fid = ch.fid)
        LEFT JOIN user_data on (user_data.fid = ch.fid)
        WHERE
            ch.channel_id = $1
            AND
            ch.strategy_name=$2
        ORDER BY rank ASC
        ),
        mapped_records as (
        SELECT top_records.*,addresses.address
        FROM top_records
        LEFT JOIN addresses using (fid)
        )
        select fid,
        any_value(fname) as fname,
        any_value(username) as username,
        any_value(pfp) as pfp,
        any_value(bio) as bio,
        any_value(rank) as rank,
        any_value(score) as score,
        ARRAY_AGG(DISTINCT address) as addresses
        FROM mapped_records
        GROUP BY fid
        ORDER by rank
        OFFSET $3
        LIMIT $4
        """
    return await fetch_rows(channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool)


async def get_profile_ranks(strategy_id: int, fids: list[int], pool: Pool, lite: bool):
    if lite:
        sql_query = """
                WITH total AS (
                    SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
                )
                SELECT
                    profile_id as fid,
                    any_value(user_data.value) as username,
                    rank,
                    score,
                    ((total.total - (rank - 1))*100 / total.total) as percentile
                FROM k3l_rank
                CROSS JOIN total
                LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
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
            any_value(fnames.fname) as fname,
            any_value(user_data.value) as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_rank
        CROSS JOIN total
        LEFT JOIN fnames on (fnames.fid = profile_id)
        LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
        WHERE
            strategy_id = $1
            AND profile_id = ANY($2::integer[])
        GROUP BY profile_id,rank,score,percentile
        ORDER BY rank
        """
    return await fetch_rows(strategy_id, fids, sql_query=sql_query, pool=pool)


async def get_channel_profile_ranks(
        channel_id: str,
        strategy_name: str,
        fids: list[int],
        lite: bool,
        pool: Pool
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
        sql_query = """
        WITH total AS (
            SELECT count(*) as total from k3l_channel_rank
            WHERE channel_id = $1
            AND strategy_name = $2
        ),
        addresses as (
        SELECT '0x' || encode(fids.custody_address, 'hex') as address, fid
        FROM fids
        union all
         SELECT v.claim->>'address' as address, fid
         FROM verifications v
        ),
        top_records as (
        SELECT
            ch.fid,
            fnames.fname as fname,
            user_data.value as username,
            rank,
            score,
            ((total.total - (rank - 1))*100 / total.total) as percentile
        FROM k3l_channel_rank as ch
        CROSS JOIN total
        LEFT JOIN fnames on (fnames.fid = ch.fid)
        LEFT JOIN user_data on (user_data.fid = ch.fid and user_data.type=6)
        WHERE
            channel_id = $1
            AND
            strategy_name = $2
            AND
            ch.fid = ANY($3::integer[])
        ORDER BY rank
        ),
        mapped_records as (
        SELECT top_records.*,addresses.address
        FROM top_records
        LEFT JOIN addresses using (fid)
        )
        SELECT
        fid,
        any_value(fname) as fname,
        any_value(username) as username,
        any_value(rank) as rank,
        any_value(score) as score,
        any_value(percentile) as percentile,
        ARRAY_AGG(DISTINCT address) as addresses
        FROM mapped_records
        GROUP BY fid
        ORDER by rank

        """
    return await fetch_rows(channel_id, strategy_name, fids, sql_query=sql_query, pool=pool)


async def get_top_frames(
        agg: ScoreAgg,
        weights: Weights,
        offset: int,
        limit: int,
        recent: bool,
        decay: bool,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight * weights.decay_factor,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(weights.score * weights.weight * weights.decay_factor,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight * weights.decay_factor)'
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    if decay:
        # WARNING: This is still under development and can lead to high latency
        decay_sql = """
            power(
                1-(1/365::numeric),
                (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - labels.latest_cast_dt)) / (60 * 60 * 24))::numeric
            )
        """
    else:
        decay_sql = "1"

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
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight * weights.decay_factor,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(weights.score * weights.weight * weights.decay_factor,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight * weights.decay_factor)'
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    if decay:
        # WARNING: This is still under development and can lead to high latency
        decay_sql = """
            power(
                1-(1/365::numeric),
                (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - labels.latest_cast_dt)) / (60 * 60 * 24))::numeric
            )
        """
    else:
        decay_sql = "1"

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
            fnames.fname||
            '/0x' ||
            substring(encode(casts.hash, 'hex'), 1, 8)
        order by casts.created_at
        ))[1:$2] as warpcast_urls
    FROM top_frames
	INNER JOIN k3l_cast_embed_url_mapping as url_map on (url_map.url_id = top_frames.url_id)
    INNER JOIN casts on (casts.id = url_map.cast_id)
    INNER JOIN fnames on (fnames.fid = casts.fid)
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
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(weights.score * weights.weight,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight)'

    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '3 days')
        """
    else:
        time_filter_sql = ""

    match voting:
        case Voting.SINGLE:
            wt_score_sql = 'max(score)'
            wt_weight_sql = f"""
                            max(case interactions.action_type
                                when 'cast' then {weights.cast}
                                when 'recast' then {weights.recast}
                                else {weights.like}
                                end)
                            """
            wt_group_by_sql = 'GROUP BY interactions.url, interactions.fid'
        case _:
            wt_score_sql = 'k3l_rank.score'
            wt_weight_sql = f"""
                            case interactions.action_type
                                when 'cast' then {weights.cast}
                                when 'recast' then {weights.recast}
                                else {weights.like}
                                end
                            """
            wt_group_by_sql = ''

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
        array_agg(distinct(fnames.fname)) as interacted_by_fnames,
        array_agg(distinct(user_data.value)) as interacted_by_usernames
    FROM weights
    LEFT JOIN fnames on (fnames.fid = weights.fid)
    LEFT JOIN user_data on (user_data.fid = weights.fid and user_data.type=6)
    GROUP BY weights.url
    ORDER by score DESC
    LIMIT $2
    """
    return await fetch_rows(json.dumps(trust_scores), limit, sql_query=sql_query, pool=pool)


async def get_popular_neighbors_casts(
        agg: ScoreAgg,
        weights: Weights,
        trust_scores: list[dict],
        offset: int,
        limit: int,
        lite: bool,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

    resp_fields = "'0x' || encode(hash, 'hex') as cast_hash," \
                  "DATE_TRUNC('hour', timestamp) as cast_hour, fid, timestamp, cast_score"

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
                    power(
                        1-(1/(365*24)::numeric),
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - action_ts)) / (60 * 60))::numeric
                    )
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
    return await fetch_rows(json.dumps(trust_scores), offset, limit, sql_query=sql_query, pool=pool)


async def get_recent_neighbors_casts(
        trust_scores: list[dict],
        offset: int,
        limit: int,
        lite: bool,
        pool: Pool
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
            fnames.fname,
            casts.text,
            casts.embeds,
            casts.mentions,
            casts.timestamp,
            power(
                1-(1/(365*24)::numeric),
                (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - casts.timestamp)) / (60 * 60))::numeric
            )* trust.score as cast_score,
        row_number() over(partition by date_trunc('hour', casts.timestamp) order by random()) as rn
        FROM k3l_recent_parent_casts as casts
        INNER JOIN  json_to_recordset($1::json)
            AS trust(fid int, score numeric)
                ON casts.fid = trust.fid
        {'LEFT' if lite else 'INNER'} JOIN fnames ON (fnames.fid = casts.fid)
        WHERE casts.deleted_at IS NULL
        ORDER BY casts.timestamp DESC, cast_score desc
        OFFSET $2
        LIMIT $3
        )
        select {resp_fields} from cast_details order by rn
    """
    return await fetch_rows(json.dumps(trust_scores), offset, limit, sql_query=sql_query, pool=pool)


async def get_recent_casts_by_fids(
        fids: list[int],
        offset: int,
        limit: int,
        pool: Pool
):
    sql_query = """
        SELECT
            '0x' || encode( casts.hash, 'hex') as cast_hash
        FROM casts
        WHERE
            casts.fid = ANY($1::integer[])
        ORDER BY casts.timestamp DESC
        OFFSET $2
        LIMIT $3
        """

    return await fetch_rows(fids, offset, limit, sql_query=sql_query, pool=pool)


async def get_popular_degen_casts(
        agg: ScoreAgg,
        weights: Weights,
        offset: int,
        limit: int,
        sorting_order: str,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

    ordering = "casts.timestamp DESC" if sorting_order == 'recent' else "date_trunc('day',c.timestamp) DESC, cast_score DESC"

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
                    power(
                        0.99::numeric, -- After 24 hours: 0.78584693
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - dt.parent_timestamp)) / (60 * 60))::numeric
                    )
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
            INNER JOIN casts c ON (c.hash = fa.cast_hash)
            ORDER BY {ordering}
        )
        SELECT cast_hash, timestamp, cast_score, fid, text, embeds, mentions
        FROM cast_details
        WHERE row_num between $1 and $2;
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_popular_channel_casts_lite(
        channel_id: str,
        channel_url: str,
        strategy_name: str,
        agg: ScoreAgg,
        weights: Weights,
        offset: int,
        limit: int,
        sorting_order: str,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

    if sorting_order == 'recent':
        ordering = True
    else:
        ordering = False

    sql_query = f"""
        with fid_cast_scores as (
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
                    power(
                        1-(1/(365*24)::numeric),
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ci.action_ts)) / (60 * 60))::numeric
                    )
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts BETWEEN now() - interval '30 days'
  										AND now() - interval '10 minutes'
                    AND casts.root_parent_url = $2)
            INNER JOIN k3l_channel_rank as fids 
                ON (fids.channel_id=$1 AND fids.fid = ci.fid AND fids.strategy_name=$3)
            LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts DESC
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
        cast_ts,
        row_number() over(partition by date_trunc('day',cast_ts) order by random()) as rn
    FROM scores
    WHERE cast_score*100000000000>100
    {"ORDER BY cast_ts desc" if ordering else "ORDER BY date_trunc('day',cast_ts) DESC, cast_score DESC"}
    OFFSET $4
    LIMIT $5
    )
    select cast_hash, cast_hour, cast_ts from cast_details

    """
    return await fetch_rows(channel_id, channel_url, strategy_name, offset, limit, sql_query=sql_query, pool=pool)


async def get_popular_channel_casts_heavy(
        channel_id: str,
        channel_url: str,
        strategy_name: str,
        agg: ScoreAgg,
        weights: Weights,
        offset: int,
        limit: int,
        sorting_order: str,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

    if sorting_order == 'recent':
        ordering = True
    else:
        ordering = False

    sql_query = f"""
        with fid_cast_scores as (
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
                    power(
                        1-(1/(365*24)::numeric),
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ci.action_ts)) / (60 * 60))::numeric
                    )
                ) as cast_score,
                MIN(ci.action_ts) as cast_ts
            FROM k3l_recent_parent_casts as casts
            INNER JOIN k3l_cast_action as ci
                ON (ci.cast_hash = casts.hash
                    AND ci.action_ts BETWEEN now() - interval '30 days'
  										AND now() - interval '10 minutes'
                    AND casts.root_parent_url = $2)
            INNER JOIN k3l_channel_rank as fids 
                ON (fids.channel_id=$1 AND fids.fid = ci.fid AND fids.strategy_name=$3)
            LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
            GROUP BY casts.hash, ci.fid
            ORDER BY cast_ts desc
            LIMIT 100000
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
        row_number() over(partition by date_trunc('day',casts.timestamp) order by random()) as rn
    FROM k3l_recent_parent_casts as casts
    INNER JOIN scores on casts.hash = scores.cast_hash
    WHERE cast_score*100000000000>100
    {"ORDER BY casts.timestamp desc" if ordering else "ORDER BY date_trunc('day',casts.timestamp) DESC, cast_score DESC"}
    OFFSET $4
    LIMIT $5
    )
    select cast_hash, cast_hour, text, embeds, mentions, fid, timestamp, cast_score
    from cast_details
    """
    return await fetch_rows(channel_id, channel_url, strategy_name, offset, limit, sql_query=sql_query, pool=pool)


async def get_trending_casts_lite(
        agg: ScoreAgg,
        weights: Weights,
        score_threshold_multiplier: int,
        offset: int,
        limit: int,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

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
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'

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


async def get_top_casters(
        offset: int,
        limit: int,
        pool: Pool
):
    sql_query = """ select cast_hash, i as fid, v as score from k3l_top_casters 
                    where date_iso = (select max(date_iso) from k3l_top_casters)
                    order by v desc
                    OFFSET $1 LIMIT $2"""
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)


async def get_top_spammers(
        offset: int,
        limit: int,
        pool: Pool
):
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
        channel_id: str,
        strategy_name: str,
        offset: int,
        limit: int,
        pool: Pool
):
    sql_query = """
    
    WITH 
    distinct_warpcast_followers as (
     SELECT 
    	distinct
        fid,
        channel_id
    FROM warpcast_followers
    WHERE channel_id = $1
    AND insert_ts=(select max(insert_ts) 
            FROM warpcast_followers where channel_id=$1)
    ),
    followers_data as (
    SELECT
        wf.fid,
        wf.channel_id,
        klcr.rank as channel_rank,
        k3l_rank.rank as global_rank,
        fnames.fname as fname,
        case user_data.type
      		when 6 then user_data.value
      	end username,
        case user_data.type
      		when 1 then user_data.value
      	end pfp,
        warpcast_members.memberat
    FROM 
        distinct_warpcast_followers wf 
        LEFT JOIN k3l_rank on (wf.fid = k3l_rank.profile_id  and k3l_rank.strategy_id = 9)
        LEFT JOIN k3l_channel_rank klcr 
            on (wf.fid = klcr.fid and wf.channel_id = klcr.channel_id and klcr.strategy_name = $2)
        LEFT JOIN fnames on (fnames.fid = wf.fid)
        LEFT JOIN user_data on (user_data.fid = wf.fid and user_data.type in (6,1))
        LEFT JOIN warpcast_members on (warpcast_members.fid = wf.fid and warpcast_members.channel_id = wf.channel_id)
    )
    SELECT 
        fid,
        channel_id,
        channel_rank,
        global_rank,
        any_value(fname) as fname,
        any_value(username) as username,
        any_value(pfp) as pfp,
        min(memberat) as memberat
    FROM followers_data
    GROUP BY fid,channel_id,channel_rank,global_rank
    ORDER BY channel_rank,global_rank NULLS LAST
    OFFSET $3
    LIMIT $4
    """

    return await fetch_rows(channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool)

async def get_top_channel_repliers(
        channel_id: str,
        strategy_name: str,
        offset: int,
        limit: int,
        pool: Pool
):
    sql_query = """
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
                AND wm.insert_ts=(select max(insert_ts) FROM warpcast_members where channel_id=$1)
               )
          INNER JOIN warpcast_channels_data as ch on (wf.channel_id = ch.id and ch.id=$1)
          AND wf.insert_ts=(select max(insert_ts) FROM warpcast_followers where channel_id=$1)
          AND wm.fid IS NULL
        ), 
        followers_data as (
            SELECT 
                nmf.fid,
                nmf.channel_id,
                '0x' || encode(casts.hash, 'hex') as cast_hash,
                klcr.rank as channel_rank,
                k3l_rank.rank as global_rank,
                fnames.fname as fname,
                case user_data.type
                    when 6 then user_data.value
                end username,
                case user_data.type
                    when 1 then user_data.value
                end pfp
            FROM
                non_member_followers as nmf
                INNER JOIN casts
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
                LEFT JOIN fnames on (fnames.fid = nmf.fid)
                LEFT JOIN user_data on (user_data.fid = nmf.fid and user_data.type in (6,1))
        )
        SELECT 
            fid,
            channel_id,
            channel_rank,
            global_rank,
            (array_agg(distinct(cast_hash)))[1:1] as cast_hash,
            any_value(fname) as fname,
            any_value(username) as username,
            any_value(pfp) as pfp
        FROM followers_data
        GROUP BY fid,channel_id,channel_rank,global_rank
        ORDER BY channel_rank,global_rank NULLS LAST
        OFFSET $3
        limit $4
   
    """

    return await fetch_rows(channel_id, strategy_name, offset, limit, sql_query=sql_query, pool=pool)

async def get_trending_channel_casts(
        channel_id: str,
        channel_url: str,
        channel_strategy: str,
        max_cast_age: int,
        agg: ScoreAgg,
        offset: int,
        limit: int,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_cast_scores.cast_score,2)))'
        case ScoreAgg.SUMSQUARE:
            agg_sql = 'sum(power(fid_cast_scores.cast_score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_cast_scores.cast_score)'


    sql_query = f"""
    WITH
    fid_cast_scores as (
                SELECT
                    hash as cast_hash,
                    SUM(
                        (
                            (1 * fids.score * ci.replied)
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
                        AND ci.action_ts BETWEEN now() - interval '{max_cast_age} day' AND now() - interval '10 minutes'
                        AND casts.root_parent_url = $2)
                INNER JOIN k3l_channel_rank as fids ON (fids.channel_id=$1 AND fids.fid = ci.fid and fids.strategy_name = $3)
                LEFT JOIN automod_data as md ON (md.channel_id=$1 AND md.affected_userid=ci.fid AND md.action='ban')
                WHERE casts.created_at BETWEEN now() - interval '{max_cast_age} day' AND now()
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
            DATE_TRUNC('hour', scores.cast_ts) AS cast_hour,
            scores.cast_ts,
            scores.cast_score,
            scores.reaction_count as reaction_count,
            ci.text,
            ci.fid,
            fids.channel_id,
            fids.rank AS channel_rank,
            k3l_rank.rank AS global_rank
        FROM scores
        INNER JOIN k3l_recent_parent_casts AS ci ON ci.hash = scores.cast_hash
        INNER JOIN k3l_rank ON (ci.fid = k3l_rank.profile_id and k3l_rank.strategy_id=9)
        INNER JOIN k3l_channel_rank AS fids ON (ci.fid = fids.fid AND fids.channel_id = $1 AND fids.strategy_name = $3)
        WHERE ci.timestamp BETWEEN now() - interval '{max_cast_age} day' AND now()
        ORDER BY scores.cast_score DESC
    )
    SELECT
        distinct
        cast_details.fid,
        cast_details.channel_id,
        cast_details.channel_rank,
        cast_details.global_rank,
        cast_details.cast_hash,
        ANY_VALUE(fnames.fname) as fname,
        ANY_VALUE(case when user_data.type = 6 then user_data.value end) as username,
        ANY_VALUE(case when user_data.type = 1 then user_data.value end)  as pfp,
        ANY_VALUE(case when user_data.type = 3 then user_data.value end) as bio,
        cast_details.cast_score,
        cast_details.reaction_count,
        cast_details.cast_hour,
        cast_details.cast_ts,
        cast_details.text
    FROM cast_details
    LEFT JOIN fnames ON (cast_details.fid = fnames.fid)
    LEFT JOIN user_data ON (cast_details.fid = user_data.fid)
    GROUP BY 
        cast_details.fid,
        cast_details.channel_id,
        cast_details.channel_rank,
        cast_details.global_rank,
        cast_details.cast_hash,
        cast_details.cast_score,
        cast_details.reaction_count,
        cast_details.cast_hour,
        cast_details.cast_ts,
        cast_details.text
    ORDER BY cast_score DESC
    OFFSET $4
    LIMIT $5
    """

    return await fetch_rows(channel_id, channel_url, channel_strategy, offset, limit, sql_query=sql_query, pool=pool)
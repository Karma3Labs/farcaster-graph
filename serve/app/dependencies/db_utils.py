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
    logger.trace(f"Execute query: {sql_query}")
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
            verifications.claim->'address' as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE
            verifications.claim->'address' = ANY($1::text[])
    UNION
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
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
            '0x' || encode(custody_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        LEFT JOIN username_proofs as proofs ON (proofs.fid = fnames.fid)
        WHERE
            (fnames.fname = ANY($1::text[]))
            OR
            (user_data.value = ANY($1::text[]))
            OR
  			(proofs.username = ANY($1::text[]))
    UNION
        SELECT
            '0x' || encode(signer_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        LEFT JOIN username_proofs as proofs ON (proofs.fid = fnames.fid)
        WHERE
            (fnames.fname = ANY($1::text[]))
            OR
            (user_data.value = ANY($1::text[]))
            OR
  			(proofs.username = ANY($1::text[]))
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
        '0x' || encode(any_value(custody_address), 'hex') as address,
        any_value(fnames.fname) as fname,
        any_value(user_data.value) as username,
        fids.fid as fid
    FROM fids
    INNER JOIN fnames ON (fids.fid = fnames.fid)
    LEFT JOIN user_data ON (user_data.fid = fids.fid and user_data.type=6)
    LEFT JOIN username_proofs as proofs ON (proofs.fid = fids.fid)
    WHERE
        (fnames.fname = ANY($1::text[]))
        OR
        (user_data.value = ANY($1::text[]))
        OR
        (proofs.username = ANY($1::text[]))
    GROUP BY fids.fid
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(handles, sql_query=sql_query, pool=pool)

async def get_all_handle_addresses_for_fids(
  fids: list[str],
  pool: Pool,
):
    sql_query = """
    (
        SELECT
            '0x' || encode(custody_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE
            fnames.fid = ANY($1::integer[])
    UNION
        SELECT
            '0x' || encode(signer_address, 'hex') as address,
            fnames.fname as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE
            fnames.fid = ANY($1::integer[])
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)

async def get_unique_handle_metadata_for_fids(
  fids: list[str],
  pool: Pool,
):
    sql_query = """
    SELECT
        '0x' || encode(any_value(custody_address), 'hex') as address,
        any_value(fnames.fname) as fname,
        any_value(user_data.value) as username,
        fids.fid as fid
    FROM fids
    INNER JOIN fnames ON (fids.fid = fnames.fid)
    LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
    WHERE
        fids.fid = ANY($1::integer[])
    GROUP BY fids.fid
    LIMIT 1000 -- safety valve
    """
    return await fetch_rows(fids, sql_query=sql_query, pool=pool)

async def get_top_profiles(strategy_id:int, offset:int, limit:int, pool: Pool):
    sql_query = """
    WITH total AS (
        SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
    )
    SELECT
        profile_id as fid,
        fnames.fname as fname,
        user_data.value as username,
        rank,
        score,
        ((total.total - (rank - 1))*100 / total.total) as percentile
    FROM k3l_rank
    CROSS JOIN total
    INNER JOIN fnames on (fnames.fid = profile_id)
    LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
    WHERE strategy_id = $1
    ORDER BY rank
    OFFSET $2
    LIMIT $3
    """
    return await fetch_rows(strategy_id, offset, limit, sql_query=sql_query, pool=pool)

async def get_profile_ranks(strategy_id:int, fids:list[int], pool: Pool):
    sql_query = """
    WITH total AS (
        SELECT count(*) as total from k3l_rank WHERE strategy_id = $1
    )
    SELECT
        profile_id as fid,
        fnames.fname as fname,
        user_data.value as username,
        rank,
        score,
        ((total.total - (rank - 1))*100 / total.total) as percentile
    FROM k3l_rank
    CROSS JOIN total
    INNER JOIN fnames on (fnames.fid = profile_id)
    LEFT JOIN user_data on (user_data.fid = profile_id and user_data.type=6)
    WHERE
        strategy_id = $1
        AND profile_id = ANY($2::integer[])
    ORDER BY rank
    """
    return await fetch_rows(strategy_id, fids, sql_query=sql_query, pool=pool)

async def get_top_frames(
        agg: ScoreAgg,
        weights: Weights,
        offset:int,
        limit:int,
        recent:bool,
        decay:bool,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight * weights.decay_factor,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(weights.score * weights.weight * weights.decay_factor,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight * weights.decay_factor)'
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels 
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '30 days')
        """
    else:
        time_filter_sql=""

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
        FROM k3l_frame_interaction as interactions
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
        offset:int,
        limit:int,
        recent:bool,
        decay:bool,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight * weights.decay_factor,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(weights.score * weights.weight * weights.decay_factor,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight * weights.decay_factor)'
    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels 
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '30 days')
        """
    else:
        time_filter_sql=""

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
        FROM k3l_frame_interaction as interactions
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
        limit:int,
        recent:bool,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(weights.score * weights.weight,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(weights.score * weights.weight)'

    if recent:
        time_filter_sql = """
            INNER JOIN k3l_url_labels as labels 
      		on (labels.url_id = interactions.url_id and labels.latest_cast_dt > now() - interval '30 days')
        """
    else:
        time_filter_sql=""

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
        FROM k3l_frame_interaction as interactions
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
    INNER JOIN fnames on (fnames.fid = weights.fid)
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
        limit:int,
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS:
            agg_sql = 'sqrt(avg(power(fid_scores.score,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(fid_scores.score,2))'
        case ScoreAgg.SUM | _:
            agg_sql = 'sum(fid_scores.score)'

    sql_query = f"""
        with fid_scores as (
            SELECT
                ci.cast_id,
                SUM(
                    (
                        ({weights.cast} * trust.score * ci.casted) 
                        + ({weights.reply} * trust.score * ci.replied)
                        + ({weights.recast} * trust.score * ci.recasted)
                        + ({weights.like} * trust.score * ci.liked)
                    )
                    *
                    power(
                        1-(1/365::numeric),
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - action_ts)) / (60 * 60 * 24))::numeric
                    )
                ) as score
            FROM json_to_recordset($1::json)
                AS trust(fid int, score numeric) 
            INNER JOIN k3l_fid_cast_action as ci
                ON (ci.fid = trust.fid
                    AND ci.action_ts BETWEEN now() - interval '10 days' 
  										AND now() - interval '10 minutes')
            GROUP BY ci.cast_id, ci.fid
            LIMIT 100000
        )
        , scores AS (
            SELECT
                cast_id,
                {agg_sql} as cast_score
                FROM fid_scores
                GROUP BY cast_id
                ORDER BY cast_score DESC
                LIMIT $2 
            )
    SELECT
        '0x' || encode(casts.cast_hash, 'hex') as cast_hash,
        casts.cast_text,
        casts.embeds as cast_embeds,
        casts.fid as cast_fid,
        cast_score
    FROM k3l_casts_replica as casts
    INNER JOIN scores on (casts.cast_id = scores.cast_id 
                            AND casts.cast_ts BETWEEN now() - interval '30 days' 
  											AND now() - interval '10 minutes')
    ORDER by cast_score DESC
    """
    return await fetch_rows(json.dumps(trust_scores), limit, sql_query=sql_query, pool=pool)

async def get_recent_neighbors_casts(
        trust_scores: list[dict],
        offset:int,
        limit:int,
        pool: Pool
):
    sql_query = f"""
        SELECT
            '0x' || encode( casts.cast_hash, 'hex') as hash,
            'https://warpcast.com/'||
            fnames.fname||
            '/0x' ||
            substring(encode(casts.cast_hash, 'hex'), 1, 8) as url,
            casts.cast_text as text,
            casts.embeds,
            casts.mentions,  
            casts.fid,
            power(
                1-(1/365::numeric),
                (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cast_ts)) / (60 * 60 * 24))::numeric
            )* trust.score as score
        FROM k3l_casts_replica as casts 
        INNER JOIN  json_to_recordset($1::json)
            AS trust(fid int, score numeric) 
                ON (casts.fid = trust.fid
                    AND casts.cast_ts BETWEEN now() - interval '30 days' 
  										AND now())
        INNER JOIN fnames ON (fnames.fid = casts.fid)
        ORDER BY casts.cast_ts DESC
        OFFSET $2
        LIMIT $3
    """
    return await fetch_rows(json.dumps(trust_scores), offset, limit, sql_query=sql_query, pool=pool)


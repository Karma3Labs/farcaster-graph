import time
import json
from ..config import settings
from ..models.frame_model import ScoreAgg, Weights
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
    logger.debug(f"executing query: {sql_query}")
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                # Run the query passing the request argument.
                rows = await connection.fetch(
                                        sql_query, 
                                        *args, 
                                        timeout=settings.POSTGRES_TIMEOUT_SECS
                                        )
    logger.info(f"db took {time.perf_counter() - start_time} secs for {len(rows)} rows")
    return rows

async def get_handle_fid_for_addresses(
    addresses: list[str],
    pool: Pool
):
    sql_query = """
    (
        SELECT 
            '0x' || encode(verifications.signer_address, 'hex') as address,
            fnames.username as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE 
            '0x' || encode(verifications.signer_address, 'hex') = ANY($1::text[])
    UNION
        SELECT
            '0x' || encode(fids.custody_address, 'hex') as address,
            fnames.username as fname,
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
            fnames.username as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        LEFT JOIN username_proofs as proofs ON (proofs.fid = fnames.fid)
        WHERE 
            (fnames.username = ANY($1::text[]))
            OR
            (user_data.value = ANY($1::text[]))
            OR
  			(proofs.username = ANY($1::text[]))
    UNION
        SELECT
            '0x' || encode(signer_address, 'hex') as address,
            fnames.username as fname,
            user_data.value as username,
            fnames.fid as fid
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        LEFT JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        LEFT JOIN username_proofs as proofs ON (proofs.fid = fnames.fid)
        WHERE 
            (fnames.username = ANY($1::text[]))
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
        any_value(fnames.username) as fname,
        any_value(user_data.value) as username,
        fids.fid as fid
    FROM fids
    INNER JOIN fnames ON (fids.fid = fnames.fid)
    LEFT JOIN user_data ON (user_data.fid = fids.fid and user_data.type=6)
    LEFT JOIN username_proofs as proofs ON (proofs.fid = fids.fid)
    WHERE 
        (fnames.username = ANY($1::text[]))
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
            fnames.username as fname,
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
            fnames.username as fname,
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
        any_value(fnames.username) as fname,
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
        fnames.username as fname,
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
        fnames.username as fname,
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
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS: 
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(weights.score * weights.weight,2))'
        case ScoreAgg.SUM | _: 
            agg_sql = 'sum(weights.score * weights.weight)'   

    sql_query = f"""
    WITH weights AS 
    (
        SELECT
            interactions.url,
            interactions.fid,
            k3l_rank.score,
            interactions.action_type,
            case interactions.action_type 
                when 'cast' then {weights.cast}
                when 'recast' then {weights.recast}
                else {weights.like}
                end as weight
        FROM k3l_frame_interaction as interactions
            INNER JOIN k3l_url_labels as labels on (labels.url_id = interactions.url_id)
        INNER JOIN 
            k3l_rank on (k3l_rank.profile_id = interactions.fid and k3l_rank.strategy_id=3)
    )
    SELECT 
        weights.url as url,
        {agg_sql} as score
        --sum(case weights.action_type when 'cast' then 1 else 0 end) as total_casts,
        --sum(case weights.action_type when 'like' then 1 else 0 end) as total_likes,
        --sum(case weights.action_type when 'recast' then 1 else 0 end) as total_recasts,
        --count(1) as total_interactions
    FROM weights
    GROUP BY weights.url
    ORDER by score DESC
    OFFSET $1
    LIMIT $2
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)

async def get_neighbors_frames(
        agg: ScoreAgg, 
        weights: Weights, 
        trust_scores: list[dict], 
        limit:int, 
        pool: Pool
):
    match agg:
        case ScoreAgg.RMS: 
            agg_sql = 'sqrt(avg(power(weights.score * weights.weight,2)))'
        case ScoreAgg.SUM_SQ:
            agg_sql = 'sum(power(weights.score * weights.weight,2))'
        case ScoreAgg.SUM | _: 
            agg_sql = 'sum(weights.score * weights.weight)'    

    sql_query = f"""
    WITH weights AS 
    (
        SELECT
            interactions.url,
            interactions.fid,
            k3l_rank.score,
            interactions.action_type,
            case interactions.action_type 
                when 'cast' then {weights.cast}
                when 'recast' then {weights.recast}
                else {weights.like}
                end as weight
        FROM k3l_frame_interaction as interactions
            INNER JOIN k3l_url_labels as labels on (labels.url_id = interactions.url_id)
        INNER JOIN 
            k3l_rank on (k3l_rank.profile_id = interactions.fid and k3l_rank.strategy_id=3)
    )
    SELECT 
        weights.url as url,
        {agg_sql} as score,
        array_agg(weights.fid::integer) as interacted_by_fids,
        array_agg(fnames.username) as interacted_by_fnames,
        array_agg(user_data.value) as interacted_by_usernames
    FROM weights
    INNER JOIN json_to_recordset($1::json)
        AS trust(fid int, score numeric) ON (trust.fid = weights.fid)
    INNER JOIN fnames on (fnames.fid = weights.fid)
    LEFT JOIN user_data on (user_data.fid = weights.fid and user_data.type=6)
    GROUP BY weights.url
    ORDER by score DESC
    LIMIT $2
    """
    return await fetch_rows(json.dumps(trust_scores), limit, sql_query=sql_query, pool=pool)

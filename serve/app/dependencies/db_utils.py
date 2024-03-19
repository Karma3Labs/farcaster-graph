import time
import json
from ..config import settings
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
    SELECT 
        profile_id as fid,
        rank, 
        score
    FROM k3l_rank 
    WHERE strategy_id = $1
    ORDER BY rank
    OFFSET $2
    LIMIT $3
    """
    return await fetch_rows(strategy_id, offset, limit, sql_query=sql_query, pool=pool)

async def get_profile_ranks(strategy_id:int, fids:list[int], pool: Pool):
    sql_query = """
    SELECT 
        profile_id as fid,
        rank, 
        score
    FROM k3l_rank 
    WHERE 
        strategy_id = $1
        AND profile_id = ANY($2::integer[])
    ORDER BY rank
    """
    return await fetch_rows(strategy_id, fids, sql_query=sql_query, pool=pool)

async def get_top_frames(offset:int, limit:int, pool: Pool):
    sql_query = """
    WITH frame_users AS (
        SELECT 
            casts.fid, urls.url
        FROM casts 
        INNER JOIN k3l_cast_embed_url_mapping as url_map on (url_map.cast_id = casts.id)
        INNER JOIN k3l_url_labels as urls on (urls.url_id = url_map.url_id and urls.category='frame')
        GROUP BY 1, 2
    )
    SELECT 
        foo.url as url,
        sqrt(avg(power(k3l_rank.score,2))) as score, -- root mean square
    --   avg(power(k3l_rank.score,2)) as score, -- mean square
    -- 	sum(k3l_rank.score) as score, -- sum
        array_agg(foo.fid::integer) as used_by
    FROM frame_users as foo
    INNER JOIN 
        k3l_rank on (k3l_rank.profile_id = foo.fid and k3l_rank.strategy_id=3)
    GROUP BY foo.url
    ORDER by score DESC
    OFFSET $1
    LIMIT $2
    """
    return await fetch_rows(offset, limit, sql_query=sql_query, pool=pool)

async def get_neighbors_frames(trust_scores: list[dict], limit:int, pool: Pool):
    sql_query = """
    WITH frame_users AS (
        SELECT 
            casts.fid, urls.url
        FROM casts 
        INNER JOIN k3l_cast_embed_url_mapping as url_map on (url_map.cast_id = casts.id)
        INNER JOIN k3l_url_labels as urls on (urls.url_id = url_map.url_id and urls.category='frame')
        GROUP BY 1, 2
    )
    SELECT 
        foo.url as url,
        sqrt(avg(power(trust.score,2))) as score, -- root mean square
    --   avg(power(trust.score,2)) as score, -- mean square
    -- 	sum(trust.score) as score, -- sum
        array_agg(foo.fid::integer) as used_by
    FROM frame_users as foo
    INNER JOIN json_to_recordset($1::json)
        AS trust(fid int, score numeric) ON (trust.fid = foo.fid)
    GROUP BY foo.url
    ORDER by score DESC
    LIMIT $2
    """
    return await fetch_rows(json.dumps(trust_scores), limit, sql_query=sql_query, pool=pool)

import time
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

async def get_rows_for_input_list(
    input: list[int|str],
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
                                        input, 
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
    return await get_rows_for_input_list(input=addresses, sql_query=sql_query, pool=pool)


async def get_addresses_for_handles(
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
  			(proofs.username = ANY(ARRAY['mxjxn.eth']))
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
  			(proofs.username = ANY(ARRAY['mxjxn.eth']))
    )
    ORDER BY username
    LIMIT 1000 -- safety valve
    """
    return await get_rows_for_input_list(input=handles, sql_query=sql_query, pool=pool)

async def get_addresses_for_fids(
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
    return await get_rows_for_input_list(input=fids, sql_query=sql_query, pool=pool)


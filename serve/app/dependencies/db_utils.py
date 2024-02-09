from ..config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from asyncpg.pool import Pool
from loguru import logger

engine = create_async_engine(
    settings.POSTGRES_ASYNC_URI,
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

async def get_handles(
  addresses: list[str],
  pool: Pool
):
    sql_query = """
    SELECT 
      distinct fnames.username as username, user_data.value as display_name
    FROM fnames
    INNER JOIN fids ON (fids.fid = fnames.fid)
    INNER JOIN verifications ON (verifications.fid = fnames.fid)
    INNER JOIN user_data ON (fids.fid = user_data.fid and user_data.type=6)
    WHERE 
        ('0x' || encode(fids.custody_address, 'hex') = ANY($1::text[]))
        OR
        ('0x' || encode(verifications.signer_address, 'hex') = ANY($1::text[]))
    """
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                # Run the query passing the request argument.
                rows = await connection.fetch(
                                        sql_query, 
                                        addresses, 
                                        timeout=settings.POSTGRES_TIMEOUT_SECS
                                        )
    return rows

async def get_addresses(
  handles: list[str],
  pool: Pool,
):
    sql_query = """
    (
        SELECT 
        '0x' || encode(custody_address, 'hex') as address,
        fnames.username as username,
        user_data.value as display_name
        FROM fnames
        INNER JOIN fids ON (fids.fid = fnames.fid)
        INNER JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE 
        (fnames.username = ANY($1::text[]))
        OR
        (user_data.value = ANY($1::text[]))
    UNION
        SELECT
        '0x' || encode(signer_address, 'hex') as address,
        fnames.username as username,
        user_data.value as display_name
        FROM fnames
        INNER JOIN verifications ON (verifications.fid = fnames.fid)
        INNER JOIN user_data ON (user_data.fid = fnames.fid and user_data.type=6)
        WHERE 
        (fnames.username = ANY($1::text[]))
        OR
        (user_data.value = ANY($1::text[]))
    )
    ORDER BY display_name
    LIMIT 1000
    """
    # Take a connection from the pool.
    async with pool.acquire() as connection:
        # Open a transaction.
        async with connection.transaction():
            with connection.query_logger(logger.trace):
                # Run the query passing the request argument.
                rows = await connection.fetch(
                                        sql_query, 
                                        handles, 
                                        timeout=settings.POSTGRES_TIMEOUT_SECS
                                        )
    return rows
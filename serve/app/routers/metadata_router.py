import time

from fastapi import APIRouter, Depends
from loguru import logger
from asyncpg.pool import Pool

from ..config import settings
from ..dependencies.db_pool import get_db

router = APIRouter(tags=["metadata"])

@router.get("/handles")
async def get_handles(
  addresses: list[str],
  pool: Pool = Depends(get_db)
):
  logger.debug(addresses)
  start_time = time.perf_counter()
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
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

@router.get("/addresses")
async def get_handles(
  handles: list[str],
  pool: Pool = Depends(get_db)
):
  logger.debug(handles)
  start_time = time.perf_counter()
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
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

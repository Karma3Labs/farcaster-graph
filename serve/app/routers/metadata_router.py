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
      '0x' || encode(fids.custody_address, 'hex') as address,
      username
    FROM fnames
    INNER JOIN fids ON (fids.fid = fnames.fid)
    WHERE 
        '0x' || encode(fids.custody_address, 'hex') = ANY($1::text[])
        -- fids.custody_address = ANY($1::bytea[])
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

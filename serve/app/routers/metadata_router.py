import time

from fastapi import APIRouter, Depends
from loguru import logger
from asyncpg.pool import Pool

from ..dependencies import db_pool, db_utils

router = APIRouter(tags=["metadata"])

@router.post("/handles")
@router.get("/handles")
async def get_handles(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  logger.debug(addresses)
  start_time = time.perf_counter()
  rows = await db_utils.get_handles(addresses, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

@router.post("/addresses")
@router.get("/addresses")
async def get_addresses(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  logger.debug(handles)
  start_time = time.perf_counter()
  rows = await db_utils.get_addresses(handles, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

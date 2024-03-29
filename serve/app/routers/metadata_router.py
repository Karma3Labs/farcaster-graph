import time

from fastapi import APIRouter, Depends
from loguru import logger
from asyncpg.pool import Pool

from ..dependencies import db_pool, db_utils

router = APIRouter(tags=["Metadata"])

@router.post("/handles")
async def get_handles_for_addresses(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of addresses, this API returns a list of handles. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  logger.debug(addresses)
  start_time = time.perf_counter()
  rows = await db_utils.get_handle_fid_for_addresses(addresses, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

@router.post("/fids")
async def get_fids_for_addresses(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of addresses, this API returns a list of fids. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  logger.debug(addresses)
  start_time = time.perf_counter()
  rows = await db_utils.get_handle_fid_for_addresses(addresses, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

@router.post("/addresses/fids")
async def get_addresses_for_fidss(
  # Example: -d '[2,3]'
  fids: list[int],
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of handles, this API returns a list of addresses. \n
  Example: [2,3] \n
  """
  logger.debug(fids)
  start_time = time.perf_counter()
  rows = await db_utils.get_all_handle_addresses_for_fids(fids, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}

@router.post("/addresses/handles")
@router.post("/addresses")
async def get_addresses_for_handles(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of handles, this API returns a list of addresses. \n
  Example: ["vitalik.eth", "dwr.eth"] \n
  """
  logger.debug(handles)
  start_time = time.perf_counter()
  rows = await db_utils.get_all_fid_addresses_for_handles(handles, pool)
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}



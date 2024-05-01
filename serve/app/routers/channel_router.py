from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from loguru import logger
from asyncpg.pool import Pool

from ..models.channel_model import Channel
from ..dependencies import  db_pool, db_utils

router = APIRouter(tags=["Channel OpenRank Scores"])

@router.get("/rankings/{channel}")
async def get_top_channel_profiles(
  channel: Annotated[Channel, Path()],
  offset: Annotated[int | None, Query()] = 0,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  lite: bool = True,
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Get a list of fids based on the engagement relationships in the given channel
    and scored by Eigentrust algorithm. \n
  Specify one of the following as channel_id:
    `degen`, `base`, `optimism`, `founders`, `farcaster`
  This API takes two optional parameters - offset and limit. \n
  Parameter 'offset' is used to specify how many results to skip 
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return. \n
  Parameter 'lite' is used to indicate if additional details like 
    fnames and percentile should be returned or not. \n
  By default, limit is 100, offset is 0 and lite is True i.e., returns top 100 fids.
  """
  ranks = await db_utils.get_top_channel_profiles(
                          channel_id=channel.value,
                          offset=offset, 
                          limit=limit,
                          lite=lite,
                          pool=pool)
  return {"result": ranks}


@router.post("/rankings/{channel}/fids")
async def get_channel_rank_for_fids(
  # Example: -d '[1, 2]'
  channel: Annotated[Channel, Path()],
  fids: list[int],  
  lite: bool = True,
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of input fids, return a list of fids
    that are ranked based on the engagement relationships in the channel
    and scored by Eigentrust algorithm. \n
    Example: [1, 2] \n
  Parameter 'lite' is used to indicate if additional details like 
    fnames and percentile should be returned or not. \n
  By default, lite is True
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  ranks = await db_utils.get_channel_profile_ranks(
                          channel_id=channel.value,
                          fids=fids, 
                          lite=lite,
                          pool=pool)
  return {"result": ranks}

@router.post("/rankings/{channel}/handles")
async def get_channel_rank_for_handles(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  channel: Annotated[Channel, Path()],
  handles: list[str],
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Given a list of input handles, return a list of handles
    that are ranked based on the engagement relationships in the channel
    and scored by Eigentrust algorithm. \n
    Example: ["dwr.eth", "varunsrin.eth"] \n
  """
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  # fetch handle-fid pairs for given handles
  handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # extract fids from the handle-fid pairs 
  fids = [hf["fid"] for hf in handle_fids]

  ranks = await db_utils.get_channel_profile_ranks(
                          channel_id=channel.value,
                          fids=fids, 
                          lite=False,
                          pool=pool)
  return {"result": ranks}

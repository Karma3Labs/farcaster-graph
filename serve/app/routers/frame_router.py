from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["frames"])

@router.get("/global/rankings")
async def get_top_frames(
  offset: Annotated[int | None, Query()] = 0,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Get a list of frame urls that are used by highly ranked profiles. \n
  This API takes two optional parameters - offset and limit. \n
  By default, limit is 100 and offset is 0 i.e., returns top 100 frame urls.
  """
  frames = await db_utils.get_top_frames(offset=offset, limit=limit, pool=pool)
  return {"result": frames}

@router.post("/personalized/rankings/fids")
async def get_personalized_frames_for_fids(
  # Example: -d '[1, 2]'
  fids: list[int],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph)
):
  """
  Given a list of input fids, return a list of frame urls 
    used by the extended trust network of the input fids. \n
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

  frames = await db_utils.get_neighbors_frames(trust_scores=trust_scores, limit=limit, pool=pool)
  return {"result": frames}

@router.post("/personalized/rankings/handles")
async def get_personalized_frames_for_handles(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph)
):
  """
  Given a list of input handles, return a list of frame urls 
    used by the extended trust network of the input handles. \n
  """
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(handles)

  # fetch handle-address pairs for given handles
  handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(handle_fids, graph_model, k, limit)

  frames = await db_utils.get_neighbors_frames(trust_scores=trust_scores, limit=limit, pool=pool)
  return {"result": frames}


from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..models.frame_model import ScoreAgg, Weights, Voting
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["frames"])

@router.get("/global/rankings")
async def get_top_frames(
  # TODO consider using path parameter for better observality
  agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.RMS,
  weights: Annotated[str | None, Query()] = 'L1C10R5',
  offset: Annotated[int | None, Query()] = 0,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db)
):
  """
  Get a list of frame urls that are used by highly ranked profiles. \n
  This API takes four optional parameters - agg, weights, offset and limit. \n
  Parameter 'agg' is used to define the aggregation function and 
    can take any of the following values - `rms`, `sumsquare`, `sum`. \n
  Parameter 'weights' is used to define the weights to be assigned
    to like, cast and recast actions by profiles. \n
  By default, agg=rms, weights='L1C10R5', offset=0 and limit=100 i.e., returns top 100 frame urls.
  """
  try:
    weights = Weights.from_str(weights)
  except:
    raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")
  frames = await db_utils.get_top_frames(agg, weights, offset=offset, limit=limit, pool=pool)
  return {"result": frames}

@router.post("/personalized/rankings/fids")
async def get_personalized_frames_for_fids(
  # Example: -d '[1, 2]'
  fids: list[int],
  # TODO consider using path parameter for better observality
  agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUM_SQ,
  weights: Annotated[str | None, Query()] = 'L1C10R5',
  voting: Annotated[Voting | None, Query()] = Voting.SINGLE,
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph)
):
  """
  Given a list of input fids, return a list of frame urls 
    used by the extended trust network of the input fids. \n
  This API takes four optional parameters - agg, weights, k and limit. \n
  Parameter 'agg' is used to define the aggregation function and 
    can take any of the following values - `rms`, `sumsquare`, `sum` \n
  Parameter 'weights' is used to define the weights to be assigned
    to like, cast and recast actions by profiles. \n
  Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
  By default, agg=rms, weights='L1C10R5', k=2 and limit=100.
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)

  try:
    weights = Weights.from_str(weights)
  except:
    raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

  frames = await db_utils.get_neighbors_frames(agg, 
                                               weights, 
                                               voting, 
                                               trust_scores=trust_scores, 
                                               limit=limit, 
                                               pool=pool)
  return {"result": frames}

@router.post("/personalized/rankings/handles")
async def get_personalized_frames_for_handles(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  # TODO consider using path parameter for better observality
  agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUM_SQ,
  weights: Annotated[str | None, Query()] = 'L1C10R5',
  voting: Annotated[Voting | None, Query()] = Voting.SINGLE,
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph)
):
  """
  Given a list of input handles, return a list of frame urls 
    used by the extended trust network of the input handles. \n
  This API takes four optional parameters - agg, weights, k and limit. \n
  Parameter 'agg' is used to define the aggregation function and 
    can take any of the following values - `rms`, `sumsquare`, `sum` \n
  Parameter 'weights' is used to define the weights to be assigned
    to like, cast and recast actions by profiles. \n
  Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
  By default, agg=rms, weights='L1C10R5',  k=2 and limit=100.
  """
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(handles)

  try:
    weights = Weights.from_str(weights)
  except:
    raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

  # fetch handle-address pairs for given handles
  handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # extract fids from the fid-handle pairs
  fids = [int(hf["fid"]) for hf in handle_fids]

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

  frames = await db_utils.get_neighbors_frames(agg, 
                                               weights, 
                                               voting,
                                               trust_scores=trust_scores, 
                                               limit=limit, 
                                               pool=pool)
  return {"result": frames}


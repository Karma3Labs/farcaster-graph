from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import PlGraph
from ..dependencies import pl_graph_utils

router = APIRouter(tags=["Personalized OpenRank Scores"])

@router.post("/engagement/fid")
async def get_personalized_engagement_for_fid(  
  fid: int,
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=5000)] = 100,
  graph_model: PlGraph = Depends(pl_graph_utils.get_engagement_graph),
):
  """
  Given a list of input fids, return a list of fids
    trusted by the extended network of the input fids. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social engagement graph 
    upto **k** degrees and until **limit** is reached. \n
  The API returns fnames and usernames by default. 
    If you want a lighter and faster response, just pass in `lite=true`. \n
  Example: [1, 2] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(fid) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fid)
  res = await _get_personalized_scores_for_fid(
                    fids=fid, 
                    k=k, 
                    limit=limit, 
                    graph_model=graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_personalized_scores_for_fid(
  fid: int,
  k: int,
  limit: int,
  graph_model: PlGraph,
) -> list[dict]: 
  # compute eigentrust on the neighbor graph using fids
  trust_scores = await pl_graph_utils.get_neighbors_scores(fid, graph_model, k, limit)

  return sorted(trust_scores, key=lambda d: d['score'], reverse=True)

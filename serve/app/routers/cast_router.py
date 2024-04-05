from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool
import requests

from ..models.graph_model import Graph
from ..models.frame_model import ScoreAgg, Weights
from ..dependencies import graph, db_pool, db_utils
from ..config import settings

router = APIRouter(tags=["Casts"])

def fetch_channel_followers(channel_id: str) -> list[int]:
  url = f'https://api.warpcast.com/v1/channel-followers?channelId={channel_id}'
  fids = []

  next_url = url
  while True:
    response = requests.get(next_url,headers = {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json'
                                },
                            timeout=settings.WARPCAST_CHANNELS_TIMEOUT)
    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    body = response.json()
    fids.extend(body['result']['fids'])
    if 'next' in body and 'cursor' in body['next'] and body['next']['cursor']:
      cursor = body['next']['cursor']
      next_url = f"{url}&cursor={cursor}"
      print(next_url)
    else:
      break
  return fids

@router.get("/personalized/{fid}")
async def get_casts_for_fid(
  fid: int,
  agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUM_SQ,
  weights: Annotated[str | None, Query()] = 'L1C10R5',
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """

  """
  try:
    weights = Weights.from_str(weights)
  except:
    raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores([fid], graph_model, k, limit)
  frames = await db_utils.get_casts_from_trusted(agg,
                                               weights,
                                               trust_scores=trust_scores,
                                               limit=limit,
                                               pool=pool)
  return {"result": frames}


@router.post("/channel/{channel_id}")
async def get_casts_by_channel_id(
  channel_id: str,
  k: int,
  limit: int,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
  agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUM_SQ,
  weights: Annotated[str | None, Query()] = 'L1C10R5',
):
  """

  """
  try:
    weights = Weights.from_str(weights)
  except:
    raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

  follower_fids = fetch_channel_followers(channel_id)
  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(follower_fids, graph_model, k, limit)
  frames = await db_utils.get_ranked_casts_from_channel(channel_id, agg,
                                               weights,
                                               trust_scores=trust_scores,
                                               limit=limit,
                                               pool=pool)
  return {"result": frames}

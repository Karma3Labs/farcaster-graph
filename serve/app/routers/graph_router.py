from typing import Annotated
import json

from fastapi import APIRouter, Depends, Query
from loguru import logger

from ..models.graph_model import Graph
from ..dependencies import graph

router = APIRouter(tags=["graphs"])

@router.post("/neighbors/engagement/addresses")
@router.get("/neighbors/engagement/addresses")
async def get_neighbors_engagement(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  logger.debug(addresses)
  res = await graph.get_neighbors_list(addresses, graph_model, k, limit)
  return {"result": res}

@router.post("/neighbors/following/addresses")
@router.get("/neighbors/following/addresses")
async def get_neighbors_following(
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_following_graph),
):
  logger.debug(addresses)
  res = await graph.get_neighbors_list(addresses, graph_model, k, limit)
  return {"result": res}

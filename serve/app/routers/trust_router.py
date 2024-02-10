from typing import Annotated

from fastapi import APIRouter, Depends, Query
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["scores"])

@router.get("/personalized/engagement/addresses")
async def get_personalized_engagement_for_addresses(  
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  logger.debug(addresses)
  res = await graph.get_neighbor_scores(addresses, graph_model, k, limit)
  return {"result": res}

@router.get("/personalized/engagement/handles")
async def get_personalized_engagement_for_addresses(  
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  logger.debug(handles)
  addrs = await db_utils.get_addresses(handles, pool)
  addresses = [addr["address"] for addr in addrs]
  res = await graph.get_neighbor_scores(addresses, graph_model, k, limit)
  return {"result": res}

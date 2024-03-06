from typing import Annotated
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

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

@router.post("/neighbors/engagement/handles")
@router.get("/neighbors/engagement/handles")
async def get_neighbors_engagement_for_handles(  
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(handles)
  res = await get_neighbors_list_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/neighbors/following/handles")
@router.get("/neighbors/following/handles")
async def get_neighbors_following_for_handles(  
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(handles)
  res = await get_neighbors_list_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_neighbors_list_for_handles(
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch handle-address pairs for given handles
  handle_addrs = await db_utils.get_addresses(handles, pool)

  # extract addresses from the handle-address pairs
  addresses = [addr["address"] for addr in handle_addrs]

  # get neighbors using addresses
  neighbor_addresses = await graph.get_neighbors_list(addresses, graph_model, k, limit)

  # fetch address-handle pairs for neighbor addresses
  neighbor_addr_handles = await db_utils.get_handles(neighbor_addresses, pool)

  # filter out input handles
  results = [ addr_handle for addr_handle in neighbor_addr_handles 
                            if not (
                              addr_handle['username'] in handles 
                              or 
                              addr_handle['fname'] in handles) 
            ] 

  return results  
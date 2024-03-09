from typing import Annotated
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["graphs"])

@router.post("/neighbors/engagement/addresses")
async def get_neighbors_engagement(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    that the input addresses have engaged with. \n
  We do a BFS traversal of the social engagement graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  logger.debug(addresses)
  res = await graph.get_neighbors_list(addresses, graph_model, k, limit)
  return {"result": res}

@router.post("/neighbors/following/addresses")
async def get_neighbors_following(
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    that the input addresses are following. \n
  We do a BFS traversal of the social follower graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  logger.debug(addresses)
  res = await graph.get_neighbors_list(addresses, graph_model, k, limit)
  return {"result": res}

@router.post("/neighbors/engagement/handles")
async def get_neighbors_engagement_for_handles(  
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input handles, return a list of handles
    that the input handles have engaged with. \n
  We do a BFS traversal of the social engagement graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
  """
  if not (1 <= len(handles) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(handles)
  res = await get_neighbors_list_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/neighbors/following/handles")
async def get_neighbors_following_for_handles(  
  # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
  handles: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input handles, return a list of handles
    that the input handles are following. \n
  We do a BFS traversal of the social follower graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
  """
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
  handle_addrs = await db_utils.get_addresses_for_handles(handles, pool)

  # extract addresses from the handle-address pairs
  addresses = [addr["address"] for addr in handle_addrs]

  # get neighbors using addresses
  neighbor_addresses = await graph.get_neighbors_list(addresses, graph_model, k, limit)

  # fetch address-handle pairs for neighbor addresses
  neighbor_addr_handles = await db_utils.get_handle_fid_for_addresses(neighbor_addresses, pool)

  # filter out input handles
  results = [ addr_handle for addr_handle in neighbor_addr_handles 
                            if not (
                              addr_handle['username'] in handles 
                              or 
                              addr_handle['fname'] in handles) 
            ] 

  return results  

@router.post("/neighbors/engagement/fids")
async def get_neighbors_engagement_for_fids(  
  # Example: -d '[1, 2]'
  fids: list[int],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input fids, return a list of fids
    that the input fids have engaged with. \n
  We do a BFS traversal of the social engagement graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: [1, 2] \n
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await get_neighbors_list_for_fids(fids, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/neighbors/following/fids")
async def get_neighbors_following_for_fids(  
  # Example: -d '[1, 2]'
  fids: list[int],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input fids, return a list of fids
    that the input fids are following. \n
  We do a BFS traversal of the social follower graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: [1, 2] \n
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await get_neighbors_list_for_fids(fids, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_neighbors_list_for_fids(
  # Example: -d '[1, 2]'
  fids: list[int],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch handle-address pairs for given fids
  fid_addrs = await db_utils.get_addresses_for_fids(fids, pool)

  # extract addresses from the handle-address pairs
  addresses = [addr["address"] for addr in fid_addrs]

  # get neighbors using addresses
  neighbor_addresses = await graph.get_neighbors_list(addresses, graph_model, k, limit)

  # fetch address-handle pairs for neighbor addresses
  neighbor_addr_handles = await db_utils.get_handle_fid_for_addresses(neighbor_addresses, pool)

  # filter out input handles
  results = [ addr_handle for addr_handle in neighbor_addr_handles 
                            if not addr_handle['fid'] in fids 
            ] 

  return results 
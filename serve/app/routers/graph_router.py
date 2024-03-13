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
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    that the input addresses have engaged with. \n
  We do a BFS traversal of the social engagement graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)

  res = await get_neighbors_list_for_addresses(addresses, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}


@router.post("/neighbors/following/addresses")
async def get_neighbors_following(
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    that the input addresses are following. \n
  We do a BFS traversal of the social follower graph 
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  """
  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)

  res = await get_neighbors_list_for_addresses(addresses, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_neighbors_list_for_addresses(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch fid-address pairs for given addresses
  addr_fid_handles = await db_utils.get_handle_fid_for_addresses(addresses, pool)

  # extract fids from the fid-address pairs
  fids = [int(addr_fid_handle['fid']) for addr_fid_handle in addr_fid_handles]
  # multiple address can have the same fid
  uniq_fids = list(set(fids))

  # get neighbors using fids
  neighbor_fids = await graph.get_neighbors_list(uniq_fids, graph_model, k, limit)

  # fetch address-fids pairs for neighbor fids
  neighbor_fid_addrs = await db_utils.get_handle_addresses_for_fids(neighbor_fids, pool)

  # filter out input addresses and return only addresses
  res = [neighbor['address'] for neighbor in neighbor_fid_addrs
                                if not neighbor['address'] in addresses]

  return res  

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
  # fetch fid-address pairs for given handles
  fid_addrs = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # extract fids from the fid-address pairs
  fids = [int(fid_addr["fid"]) for fid_addr in fid_addrs]

  # get neighbors using fids
  neighbor_fids = await graph.get_neighbors_list(fids, graph_model, k, limit)

  # fetch address-handle pairs for neighbor addresses
  neighbor_fid_handles = await db_utils.get_handle_addresses_for_fids(neighbor_fids, pool)

  # filter out input handles
  results = [ neighbor for neighbor in neighbor_fid_handles 
                            if not (
                              neighbor['username'] in handles 
                              or 
                              neighbor['fname'] in handles) 
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
  # get neighbors using fids
  neighbor_fids = await graph.get_neighbors_list(fids, graph_model, k, limit)

  # fetch address-handle pairs for neighbor fids
  neighbor_addr_handles = await db_utils.get_handle_addresses_for_fids(neighbor_fids, pool)

  # filter out input fids
  results = [ addr_handle for addr_handle in neighbor_addr_handles 
                            if not addr_handle['fid'] in fids 
            ] 

  return results 

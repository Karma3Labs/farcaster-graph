from typing import Annotated
import json

from fastapi import APIRouter, Body, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["Graphs"])

@router.post("/neighbors/engagement/addresses")
async def get_neighbors_engagement(
  addresses: Annotated[list[str], Body(
    title="Addresses",
    description="A list of addresses.",
    examples=[
      ["0x4114e33eb831858649ea3702e1c9a2db3f626446","0x8773442740c17c9d0f0b87022c722f9a136206ed"]
    ]
  )],
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

  res = await _get_neighbors_list_for_addresses(addresses, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}


@router.post("/neighbors/following/addresses")
async def get_neighbors_following(
  addresses: Annotated[list[str], Body(
    title="Addresses",
    description="A list of addresses.",
    examples=[
      ["0x4114e33eb831858649ea3702e1c9a2db3f626446","0x8773442740c17c9d0f0b87022c722f9a136206ed"]
    ]
  )],
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

  res = await _get_neighbors_list_for_addresses(addresses, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_neighbors_list_for_addresses(
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
  neighbor_fid_addrs = await db_utils.get_all_handle_addresses_for_fids(neighbor_fids, pool)

  # filter out input addresses and return only addresses
  res = [neighbor['address'] for neighbor in neighbor_fid_addrs
                                if not neighbor['address'] in addresses]

  return res

@router.post("/neighbors/engagement/handles")
async def get_neighbors_engagement_for_handles(
  handles: Annotated[list[str], Body(
    title="Handles",
    description="A list of handles.",
    examples=[
      [
        "farcaster.eth",
        "varunsrin.eth",
        "farcaster",
        "v"
      ]
    ]
  )],
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
  res = await _get_neighbors_list_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/neighbors/following/handles")
async def get_neighbors_following_for_handles(
  handles: Annotated[list[str], Body(
    title="Handles",
    description="A list of handles.",
    examples=[
      [
        "farcaster.eth",
        "varunsrin.eth",
        "farcaster",
        "v"
      ]
    ]
  )],
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
  res = await _get_neighbors_list_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_neighbors_list_for_handles(
  handles: list[str],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]:
  # fetch fid-address pairs for given handles
  handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # extract fids from the fid-handle pairs
  fids = [int(hf["fid"]) for hf in handle_fids]

  # get neighbors using fids
  neighbor_fids = await graph.get_neighbors_list(fids, graph_model, k, limit)

  # fetch address-handle pairs for neighbor addresses
  neighbor_fid_handles = await db_utils.get_unique_handle_metadata_for_fids(neighbor_fids, pool)

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
  fids: Annotated[list[int], Body(
    title="Farcaster IDs",
    description="A list of FIDs.",
    examples=[
      [1,2,3]
    ]
  )],
  k: Annotated[int, Query(le=5)] = 2,
  lite: Annotated[bool, Query()] = False,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input fids, return a list of fids
    that the input fids have engaged with. \n
  We do a BFS traversal of the social engagement graph
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  The API returns fnames and usernames by default. 
    If you want a lighter and faster response, just pass in `lite=true`. \n
  Example: [1, 2] \n
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await _get_neighbors_list_for_fids(fids, k, limit, lite, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/neighbors/following/fids")
async def get_neighbors_following_for_fids(
  fids: Annotated[list[int], Body(
    title="Farcaster IDs",
    description="A list of FIDs.",
    examples=[
      [1,2,3]
    ]
  )],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  lite: Annotated[bool, Query()] = False,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input fids, return a list of fids
    that the input fids are following. \n
  We do a BFS traversal of the social follower graph
    upto **k** degrees and terminate traversal when **limit** is reached. \n
  The API returns fnames and usernames by default. 
    If you want a lighter and faster response, just pass in `lite=true`. \n
  Example: [1, 2] \n
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await _get_neighbors_list_for_fids(fids, k, limit, lite, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}


async def _get_neighbors_list_for_fids(
  # Example: -d '[1, 2]'
  fids: list[int],
  k: int,
  limit: int,
  lite: bool,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]:
  # get neighbors using fids
  neighbor_fids = await graph.get_neighbors_list(fids, graph_model, k, limit)

  if lite: 
    return neighbor_fids

  # fetch address-handle pairs for neighbor fids
  neighbor_addr_handles = await db_utils.get_unique_handle_metadata_for_fids(neighbor_fids, pool)

  # filter out input fids
  results = [ addr_handle for addr_handle in neighbor_addr_handles
                            if not addr_handle['fid'] in fids
            ]

  return results

from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["scores"])

@router.post("/personalized/engagement/addresses")
@router.get("/personalized/engagement/addresses")
async def get_personalized_engagement_for_addresses(  
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)
  res = await graph.get_neighbors_scores(addresses, graph_model, k, limit)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/personalized/following/addresses")
@router.get("/personalized/following/addresses")
async def get_personalized_following_for_addresses(  
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph_model: Graph = Depends(graph.get_following_graph),
):
  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)
  scores = await graph.get_neighbors_scores(addresses, graph_model, k, limit)

  # filter out the input address
  res = [ score for score in scores if not score['address'] in addresses]
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/personalized/engagement/handles")
@router.get("/personalized/engagement/handles")
async def get_personalized_engagement_for_handles(  
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
  res = await get_personalized_scores_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/personalized/following/handles")
@router.get("/personalized/following/handles")
async def get_personalized_following_for_handles(  
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
  res = await get_personalized_scores_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_personalized_scores_for_handles(
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

  # compute eigentrust on the neighbor graph using addresses
  trust_scores = await graph.get_neighbors_scores(addresses, graph_model, k, limit)

  # extract addresses from the address-score pairs
  trusted_addresses = [ score['address'] for score in trust_scores ]

  # fetch address-handle pairs for trusted neighbor addresses
  trusted_addr_handles = await db_utils.get_handles(trusted_addresses, pool)

  # convert list of address-handle pairs that we got ...
  # ... from the db into a hashmap with address as key
  # [{address,handle}] into {address -> {address,handle}}
  trusted_addrs_handles_map = {}
  for addr_handle in trusted_addr_handles:
    trusted_addrs_handles_map[addr_handle['address']]=addr_handle

  # for every address-score pair, combine address and score with handle
  # {address,score} into {address,score,fname,username}
  def trust_score_with_handle(trust_score: dict) -> dict:
    addr_handle = trusted_addrs_handles_map[trust_score['address']]
    # filter out input handles
    if addr_handle and not (addr_handle['username'] in handles or 
                            addr_handle['fname'] in handles 
    ): 
      return {'address': addr_handle['address'], 
              'fname': addr_handle['fname'],
              'username': addr_handle['username'],
              'score': trust_score['score']
              }
    return None
  # end of def trust_score_with_handle

  results = [ trust_score_with_handle(trust_score) for trust_score in trust_scores]
  # filter out nulls from the previous step
  results = [ result for result in results if result is not None]
  return results  




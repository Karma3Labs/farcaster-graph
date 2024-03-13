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
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    trusted by the extended network of the input addresses. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social engagement graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """

  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)
  scores = await get_personalized_scores_for_addresses(addresses, k, limit, pool, graph_model)

  # filter out the input address
  res = [ score for score in scores if not score['address'] in addresses]
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/personalized/following/addresses")
@router.get("/personalized/following/addresses")
async def get_personalized_following_for_addresses(  
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input addresses, return a list of addresses
    trusted by the extended network of the input addresses. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social following graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(addresses) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(addresses)
  scores = await get_personalized_scores_for_addresses(addresses, k, limit, pool, graph_model)

  # filter out the input address
  res = [ score for score in scores if not score['address'] in addresses]
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_personalized_scores_for_addresses(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch handle-address pairs for given fids
  addr_fid_handles = await db_utils.get_handle_fid_for_addresses(addresses, pool)

  # extract fids from the fid-address pairs typecasting to int just to be sure
  in_fids = [int(addr_fid_handle['fid']) for addr_fid_handle in addr_fid_handles]
  # multiple address can have the same fid, remove duplicates
  in_fids = list(set(in_fids))

  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(in_fids, graph_model, k, limit)

  # convert list of fid scores into a lookup with fid as key
  # [{fid1,score},{fid2,score}] -> {fid1:score, fid2:score}
  trusted_score_fid_map = {ts['fid']:ts['score'] for ts in trust_scores }

  # extract fids from the trusted neighbor fid-score pairs
  trusted_fids = list(trusted_score_fid_map.keys())

  # fetch address-handle pairs for trusted neighbor fids
  trusted_addr_handle_fids = await db_utils.get_handle_addresses_for_fids(trusted_fids, pool)

  # for every address-score pair, combine address and score with handle and fid
  # {address,score} into {address,score,fname,username,fid}
  def fn_include_score(trusted_addr_handle_fid: dict) -> dict:
    trusted_addr_handle_fid['score'] = trusted_fids[trusted_addr_handle_fid['fid']]
    return trusted_addr_handle_fid
  # end of def fn_trust_score_with_handle_fid

  results = map(fn_include_score, trusted_addr_handle_fids)

  # filter out nulls from the previous step
  results = [ result for result in results if result is not None]
  return results  

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
  """
  Given a list of input handles, return a list of handles
    trusted by the extended network of the input handles. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social engagement graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
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
  """
  Given a list of input handles, return a list of handles
    trusted by the extended network of the input handles. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social following graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
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
  handle_addrs = await db_utils.get_fid_addresses_for_handles(handles, pool)

  # extract addresses from the handle-address pairs
  addresses = [addr["address"] for addr in handle_addrs]

  # compute eigentrust on the neighbor graph using addresses
  trust_scores = await graph.get_neighbors_scores(addresses, graph_model, k, limit)

  # extract addresses from the address-score pairs
  trusted_addresses = [ score['address'] for score in trust_scores ]

  # fetch address-handle pairs for trusted neighbor addresses
  trusted_addr_handle_fids = await db_utils.get_handle_fid_for_addresses(trusted_addresses, pool)

  # convert list of address-handle pairs that we got ...
  # ... from the db into a hashmap with address as key
  # [{address,handle}] into {address -> {address,handle}}
  trusted_addrs_handle_fids_map = {}
  for addr_handle_fid in trusted_addr_handle_fids:
    trusted_addrs_handle_fids_map[addr_handle_fid['address']]=addr_handle_fid

  # for every address-score pair, combine address and score with handle
  # {address,score} into {address,score,fname,username}
  def fn_trust_score_with_handle(trust_score: dict) -> dict:
    addr_handle_fid = trusted_addrs_handle_fids_map.get(trust_score['address'], None)
    # filter out input handles
    if not addr_handle_fid \
        or addr_handle_fid['username'] in handles \
        or addr_handle_fid['fname'] in handles: 
      return None
    return {'address': addr_handle_fid['address'], 
            'fname': addr_handle_fid['fname'],
            'username': addr_handle_fid['username'],
            'score': trust_score['score']
            }
  # end of def fn_trust_score_with_handle

  results = [ fn_trust_score_with_handle(trust_score) for trust_score in trust_scores]
  # filter out nulls from the previous step
  results = [ result for result in results if result is not None]
  return results  

@router.post("/personalized/engagement/fids")
async def get_personalized_engagement_for_fids(  
  # Example: -d '[1, 2]'
  fids: list[int],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_engagement_graph),
):
  """
  Given a list of input fids, return a list of fids
    trusted by the extended network of the input fids. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social engagement graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: [1, 2] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await get_personalized_scores_for_fids(fids, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/personalized/following/fids")
async def get_personalized_following_for_fids(  
  # Example: -d '[1, 2]'
  fids: list[int],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db),
  graph_model: Graph = Depends(graph.get_following_graph),
):
  """
  Given a list of input fids, return a list of fids
    trusted by the extended network of the input fids. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social following graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: [1, 2] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await get_personalized_scores_for_fids(fids, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def get_personalized_scores_for_fids(
  # Example: -d '[1, 2]'
  fids: list[int],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch handle-address pairs for given fids
  fid_addrs = await db_utils.get_handle_addresses_for_fids(fids, pool)

  # extract addresses from the handle-address pairs
  addresses = [addr["address"] for addr in fid_addrs]

  # compute eigentrust on the neighbor graph using addresses
  trust_scores = await graph.get_neighbors_scores(addresses, graph_model, k, limit)

  # extract addresses from the address-score pairs
  trusted_addresses = [ score['address'] for score in trust_scores ]

  # fetch address-handle pairs for trusted neighbor addresses
  trusted_addr_handle_fids = await db_utils.get_handle_fid_for_addresses(trusted_addresses, pool)

  # convert list of address-handle pairs that we got ...
  # ... from the db into a hashmap with address as key
  # [{address,handle}] into {address -> {address,handle,fid}}
  trusted_addrs_handle_fids_map = {}
  for addr_handle_fid in trusted_addr_handle_fids:
    trusted_addrs_handle_fids_map[addr_handle_fid['address']]=addr_handle_fid

  # for every address-score pair, combine address and score with handle and fid
  # {address,score} into {address,score,fname,username,fid}
  def fn_trust_score_with_handle_fid(trust_score: dict) -> dict:
    addr_handle_fid = trusted_addrs_handle_fids_map.get(trust_score['address'], None)
    # filter out input handles
    if not addr_handle_fid \
        or addr_handle_fid['fid'] in fids: 
      return None
    return {'address': addr_handle_fid['address'], 
            'fname': addr_handle_fid['fname'],
            'username': addr_handle_fid['username'],
            'fid': addr_handle_fid['fid'],
            'score': trust_score['score']
            }
  # end of def fn_trust_score_with_handle_fid

  results = [ fn_trust_score_with_handle_fid(trust_score) for trust_score in trust_scores]
  # filter out nulls from the previous step
  results = [ result for result in results if result is not None]
  return results  
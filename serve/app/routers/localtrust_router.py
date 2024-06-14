from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import Graph
from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["Personalized OpenRank Scores"])

@router.post("/engagement/addresses")
async def get_personalized_engagement_for_addresses(  
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
  res = await _get_personalized_scores_for_addresses(addresses, k, limit, pool, graph_model)

  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/following/addresses")
async def get_personalized_following_for_addresses(  
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
  res = await _get_personalized_scores_for_addresses(addresses, k, limit, pool, graph_model)

  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_personalized_scores_for_addresses(
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
  fids = [int(addr_fid_handle['fid']) for addr_fid_handle in addr_fid_handles]
  # multiple address can have the same fid, remove duplicates
  fids = list(set(fids))

  res = await _get_personalized_scores_for_fids(
                    fetch_all_addrs=True, 
                    fids=fids, 
                    k=k, 
                    limit=limit, 
                    lite=False,
                    pool=pool, 
                    graph_model=graph_model)

  return res  

@router.post("/engagement/handles")
async def get_personalized_engagement_for_handles(
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
  res = await _get_personalized_scores_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/following/handles")
async def get_personalized_following_for_handles(  
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
  res = await _get_personalized_scores_for_handles(handles, k, limit, pool, graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_personalized_scores_for_handles(
  handles: list[str],
  k: int,
  limit: int,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # fetch handle-address pairs for given handles
  handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

  # extract fids from the handle-fid pairs 
  fids = [hf["fid"] for hf in handle_fids]
  res = await _get_personalized_scores_for_fids(
                    fetch_all_addrs=False, 
                    fids=fids, 
                    k=k, 
                    limit=limit,
                    lite=False, 
                    pool=pool, 
                    graph_model=graph_model)

  return res  

@router.post("/engagement/fids")
async def get_personalized_engagement_for_fids(  
  fids: Annotated[list[int], Body(
    title="Farcaster IDs",
    description="A list of FIDs.",
    examples=[
      [1,2,3]
    ]
  )],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=5000)] = 100,
  lite: Annotated[bool, Query()] = False,
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
  The API returns fnames and usernames by default. 
    If you want a lighter and faster response, just pass in `lite=true`. \n
  Example: [1, 2] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await _get_personalized_scores_for_fids(
                    fetch_all_addrs=False, 
                    fids=fids, 
                    k=k, 
                    limit=limit, 
                    lite=lite,
                    pool=pool, 
                    graph_model=graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

@router.post("/following/fids")
async def get_personalized_following_for_fids(  
  fids: Annotated[list[int], Body(
    title="Farcaster IDs",
    description="A list of FIDs.",
    examples=[
      [1,2,3]
    ]
  )],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=5000)] = 100,
  lite: Annotated[bool, Query()] = False,
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
  The API returns fnames and usernames by default. 
    If you want a lighter and faster response, just pass in `lite=true`. \n
  Example: [1, 2] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  if not (1 <= len(fids) <= 100):
    raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
  logger.debug(fids)
  res = await _get_personalized_scores_for_fids(
                    fetch_all_addrs=False, 
                    fids=fids, 
                    k=k, 
                    limit=limit, 
                    lite=lite,
                    pool=pool, 
                    graph_model=graph_model)
  logger.debug(f"Result has {len(res)} rows")
  return {"result": res}

async def _get_personalized_scores_for_fids(
  # Example: -d '[1, 2]'
  fetch_all_addrs: bool,
  fids: list[int],
  k: int,
  limit: int,
  lite: bool,
  pool: Pool,
  graph_model: Graph,
) -> list[dict]: 
  # compute eigentrust on the neighbor graph using fids
  trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

  if lite:
    return sorted(trust_scores, key=lambda d: d['score'], reverse=True)

  # convert list of fid scores into a lookup with fid as key
  # [{fid1,score},{fid2,score}] -> {fid1:score, fid2:score}
  trusted_fid_score_map = {ts['fid']:ts['score'] for ts in trust_scores }

  # extract fids from the trusted neighbor fid-score pairs
  trusted_fids = list(trusted_fid_score_map.keys())

  # fetch handle info for trusted neighbor fids
  trusted_fid_addr_handles = \
    await db_utils.get_all_handle_addresses_for_fids(trusted_fids, pool) \
    if fetch_all_addrs else \
    await db_utils.get_unique_handle_metadata_for_fids(trusted_fids, pool)


  # for every handle-fid pair, get score from corresponding fid
  # {address,fname,username,fid} into {address,fname,username,fid,score}
  def fn_include_score(trusted_fid_addr_handle: dict) -> dict:
    score = trusted_fid_score_map[trusted_fid_addr_handle['fid']]
    # trusted_fid_addr_handle is an 'asyncpg.Record'
    # 'asyncpg.Record' object does not support item assignment
    # need to create a new object with score
    return {'address': trusted_fid_addr_handle['address'], 
            'fname': trusted_fid_addr_handle['fname'],
            'username': trusted_fid_addr_handle['username'],
            'fid': trusted_fid_addr_handle['fid'],
            'score': score
            }
  # end of def fn_trust_score_with_handle_fid


  results = list(map(fn_include_score, trusted_fid_addr_handles))
  # sort by score
  results = sorted(results, key=lambda d: d['score'], reverse=True)

  return results  


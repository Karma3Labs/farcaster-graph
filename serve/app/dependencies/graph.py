from typing import Annotated
import itertools
import time
import requests

import pandas
import numpy as np
import igraph
from loguru import logger
from fastapi import Request, Query, HTTPException

from ..config import settings
from ..models.graph_model import Graph, GraphType

# dependency to make it explicit that routers are accessing hidden state
# to avoid model name hardcoding in routers
# TODO clean up hardcoded names; use enums
def get_following_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.following]

def get_engagement_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.engagement]

def is_vertex(ig: igraph.GraphBase, addr:str) -> bool:
  try:
      ig.vs.find(name=addr)
      logger.debug(addr)
      return True
  except:
      return False


async def go_eigentrust(
    pretrust: list[dict],
    max_pt_id: np.int64,
    localtrust: list[dict],
    max_lt_id: np.int64,
):

  req = {
  	"pretrust": {
  		"scheme": 'inline',
  		"size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
  		"entries": pretrust,
  	},
    "localTrust": {
  		"scheme": 'inline',
  		"size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
  		"entries": localtrust,
  	},
  	"alpha": settings.EIGENTRUST_ALPHA, 
  	"epsilon": settings.EIGENTRUST_EPSILON,
    "max_iterations": settings.EIGENTRUST_MAX_ITER,
  	"flatTail": settings.EIGENTRUST_FLAT_TAIL
  }

  logger.debug(req)
  response = requests.post(f"{settings.GO_EIGENTRUST_URL}/basic/v1/compute",
                           json=req,
                           headers = {
                              'Accept': 'application/json',
                              'Content-Type': 'application/json'
                              },
                           timeout=settings.GO_EIGENTRUST_TIMEOUT_MS)

  if response.status_code != 200:
      logger.error(f"Server error: {response.status_code}:{response.reason}")
      raise HTTPException(status_code=500, detail="Unknown error")
  trustscores = response.json()['entries']
  return trustscores

async def get_neighbor_scores(
  addresses: list[str],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> list[dict]:
  df = await _get_neighbors_edges(addresses, graph, max_degree, max_neighbors)

  # go-et expects ids.
  # convert input addresses to ids by looking up the i_code column in the edges dataframe
  pt_series = df[df['i'].isin(addresses)].groupby(by='i').first()['i_code']
  pt_len = len(pt_series)
  pretrust = [{'i': id, 'v': 1/pt_len} for id in pt_series]
  max_pt_id = max(pt_series)
  
  # go-et expects ids as 'i' and 'j' 
  # rename i_code and j_code to 'i' and 'j'
  # this rename only happens on this small localtrust slice 
  lt_df = df[['i_code', 'j_code', 'v']].rename(columns={'i_code': 'i', 'j_code': 'j'})
  localtrust = lt_df.to_dict(orient="records")
  max_lt_id = max(lt_df['i'].max(), lt_df['j'].max())

  i_scores = await go_eigentrust(pretrust=pretrust, 
                             max_pt_id=max_pt_id,
                             localtrust=localtrust,
                             max_lt_id=max_lt_id
                            )
  # we get back {'i': some_icode, 'v': some_score}
  # lookup address corresponding to some_icode in idx
  # return {'i': some_address, 'v': some_score}
  addr_scores = [ {'address': graph.idx.iloc[score['i']][0], 'score': score['v']} for score in i_scores ]
  return addr_scores

async def get_neighbors_edges_json(  
  addresses: list[str],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> str:
   df = await _get_neighbors_edges(addresses, graph, max_degree, max_neighbors)
   return df[['i', 'j', 'v']].to_json(orient="records")

async def _get_neighbors_edges(  
  addresses: list[str],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> pandas.DataFrame: 
  start_time = time.perf_counter()
  neighbors = await _fetch_korder_neighbors(addresses, graph, max_degree, max_neighbors)
  logger.info(f"graph took {time.perf_counter() - start_time} secs for {len(neighbors)} neighbors")
  logger.debug(neighbors)
  start_time = time.perf_counter()
  res = graph.df[graph.df['i'].isin(neighbors) & graph.df['j'].isin(neighbors)]
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs for {len(res)} edges")
  return res

async def _fetch_korder_neighbors(
  addresses: list[str],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> list :
  addresses = list(filter(lambda x: is_vertex(graph.graph, x), addresses))
  if len(addresses) <= 0:
    raise HTTPException(status_code=404, detail="Invalid Addresses")
  try:
    klists = []
    mindist_and_order = 1
    limit = max_neighbors
    while mindist_and_order <= max_degree:
        neighbors = graph.graph.neighborhood(
            addresses, order=mindist_and_order, mode="out", mindist=mindist_and_order
        )
        klists.append(graph.graph.vs[neighbors[0][:limit]]["name"])
        limit = limit - len(neighbors[0])
        if limit <= 0:
            break # we have reached limit of neighbors
        mindist_and_order += 1
    # end of while
    return list(itertools.chain(addresses, *klists))
  except ValueError:
    raise HTTPException(status_code=404, detail="Neighbors not found")
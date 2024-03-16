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
# TODO clean up hardcoded names in function names; use enums
def get_following_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.following]

def get_engagement_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.engagement]

def is_vertex(ig: igraph.GraphBase, addr:str) -> bool:
  try:
      ig.vs.find(name=addr)
      logger.trace(addr)
      return True
  except:
      return False


async def go_eigentrust(
    pretrust: list[dict],
    max_pt_id: np.int64,
    localtrust: list[dict],
    max_lt_id: np.int64,
):
  start_time = time.perf_counter()
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

  logger.trace(req)
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
  logger.info(f"eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores")
  return trustscores

async def get_neighbors_scores(
  fids: list[int],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> list[dict]:
  df = await _get_neighbors_edges(fids, graph, max_degree, max_neighbors)

  pt_len = len(fids)
  pretrust = [{'i': id, 'v': 1/pt_len} for id in fids]
  max_pt_id = max(fids)
  
  localtrust = df.to_dict(orient="records")
  max_lt_id = max(df['i'].max(), df['j'].max())

  i_scores = await go_eigentrust(pretrust=pretrust, 
                             max_pt_id=max_pt_id,
                             localtrust=localtrust,
                             max_lt_id=max_lt_id
                            )
  
  # rename i and v to fid and score respectively
  # also, filter out input fids
  fid_scores = [ {'fid': score['i'], 'score': score['v']} for score in i_scores if score['i'] not in fids]

  return fid_scores

async def get_neighbors_list(  
  fids: list[int],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> str:
  df = await _get_neighbors_edges(fids, graph, max_degree, max_neighbors)
  # WARNING we are operating on a shared dataframe...
  # ...inplace=False by default, explicitly setting here for emphasis
  out_df = df.groupby(by='j')[['v']].sum().sort_values(by=['v'], ascending=False, inplace=False)
  return out_df.index.to_list()

async def _get_neighbors_edges(  
  fids: list[int],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> pandas.DataFrame: 
  start_time = time.perf_counter()
  neighbors = await _fetch_korder_neighbors(fids, graph, max_degree, max_neighbors)
  logger.info(f"graph took {time.perf_counter() - start_time} secs for {len(neighbors)} neighbors")
  logger.trace(neighbors)
  start_time = time.perf_counter()
  res = graph.df[graph.df['i'].isin(neighbors) & graph.df['j'].isin(neighbors)]
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs for {len(res)} edges")
  return res

async def _fetch_korder_neighbors(
  fids: list[int],
  graph: Graph,        
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> list :
  fids = list(filter(lambda x: is_vertex(graph.graph, x), fids))
  if len(fids) <= 0:
    raise HTTPException(status_code=404, detail="Invalid fids")
  try:
    klists = []
    mindist_and_order = 1
    limit = max_neighbors
    while mindist_and_order <= max_degree:
        neighbors = graph.graph.neighborhood(
            fids, order=mindist_and_order, mode="out", mindist=mindist_and_order
        )
        # TODO prune the graph after sorting by edge weight
        klists.append(graph.graph.vs[neighbors[0][:limit]]["name"])
        limit = limit - len(neighbors[0])
        if limit <= 0:
            break # we have reached limit of neighbors
        mindist_and_order += 1
    # end of while
    return list(itertools.chain(fids, *klists))
  except ValueError:
    raise HTTPException(status_code=404, detail="Neighbors not found")
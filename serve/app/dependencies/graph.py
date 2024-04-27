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

def find_vertex_idx(ig: igraph.GraphBase, fid:int) -> int:
  try:
      logger.debug(fid)
      return ig.vs.find(name=fid).index
  except:
      return None


async def go_eigentrust(
    pretrust: list[dict],
    # max_pt_id: np.int64,
    max_pt_id: int,
    localtrust: list[dict],
    # max_lt_id: np.int64,
    max_lt_id: int,
):
  start_time = time.perf_counter()
  req = {
  	"pretrust": {
  		"scheme": 'inline',
  		# "size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
      "size": max_pt_id,
  		"entries": pretrust,
  	},
    "localTrust": {
  		"scheme": 'inline',
  		# "size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
      "size": max_lt_id,
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

  if df.shape[0] < 1:
    raise HTTPException(status_code=404, detail="No neighbors")

  stacked = df.loc[:, ('i','j')].stack()
  pseudo_id, orig_id = stacked.factorize()

  # pseudo_df is a new dataframe to avoid modifying existing shared global df 
  pseudo_df = pandas.Series(pseudo_id, index=stacked.index).unstack()
  pseudo_df.loc[:,('v')] = df.loc[:,('v')]

  pt_len = len(fids)
  # pretrust = [{'i': fid, 'v': 1/pt_len} for fid in fids]
  pretrust = [{'i': orig_id.get_loc(fid), 'v': 1/pt_len} for fid in fids]
  # max_pt_id = max(fids)
  max_pt_id = len(orig_id)
  
  localtrust = pseudo_df.to_dict(orient="records")
  # max_lt_id = max(df['i'].max(), df['j'].max())
  max_lt_id = len(orig_id)
  
  logger.info(f"max_lt_id:{max_lt_id}, localtrust size:{len(localtrust)}," \
               f" max_pt_id:{max_pt_id}, pretrust size:{len(pretrust)}")
  logger.trace(f"localtrust:{localtrust}")
  logger.trace(f"pretrust:{pretrust}")

  i_scores = await go_eigentrust(pretrust=pretrust, 
                             max_pt_id=max_pt_id,
                             localtrust=localtrust,
                             max_lt_id=max_lt_id
                            )
  
  logger.trace(f"i_scores:{i_scores}")

  # rename i and v to fid and score respectively
  # also, filter out input fids
  fid_scores = [ {'fid': int(orig_id[score['i']]), 'score': score['v']} for score in i_scores if score['i'] not in fids]
  logger.debug(f"fid_scores:{fid_scores}")
  return fid_scores

async def get_neighbors_list(  
  fids: list[int],
  graph: Graph,        
  max_degree: int,
  max_neighbors: int,
) -> str:
  df = await _get_neighbors_edges(fids, graph, max_degree, max_neighbors)
  # WARNING we are operating on a shared dataframe...
  # ...inplace=False by default, explicitly setting here for emphasis
  out_df = df.groupby(by='j')[['v']].sum().sort_values(by=['v'], ascending=False, inplace=False)
  return out_df.index.to_list()

async def _get_neighbors_edges(  
  fids: list[int],
  graph: Graph,        
  max_degree: int,
  max_neighbors: int,
) -> pandas.DataFrame: 
  start_time = time.perf_counter()
  neighbors_df = await _get_direct_edges_df(fids, graph, max_neighbors)
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs for {len(neighbors_df)} first degree edges")
  logger.trace(f"first degree edges: {neighbors_df.to_dict('records')}")
  max_neighbors = max_neighbors - len(neighbors_df)
  if max_neighbors > 0:
    start_time = time.perf_counter()
    k_neighbors_list = await _fetch_korder_neighbors(fids, graph, max_degree, max_neighbors, min_degree=2)
    logger.info(f"{graph.type} took {time.perf_counter() - start_time} secs for {len(k_neighbors_list)} neighbors")
    logger.trace(f"k degree neighors: {k_neighbors_list}")
    if settings.USE_PANDAS_PERF:
      # if multiple CPU cores are available
      k_df = graph.df.query('i in @k_neighbors_list & j in @k_neighbors_list')
    else:
      k_df = graph.df[graph.df['i'].isin(k_neighbors_list) & graph.df['j'].isin(k_neighbors_list)]
    neighbors_df = pandas.concat([neighbors_df, k_df])
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs for {len(neighbors_df)} edges")
  logger.trace(f"neighbors: {neighbors_df}")
  return neighbors_df

async def _fetch_korder_neighbors(
  fids: list[int],
  graph: Graph,        
  max_degree: int,
  max_neighbors: int,
  min_degree: int = 1
) -> list :
  
  # vids = [find_vertex_idx(graph.graph, fid) for fid in fids]
  # vids = list(filter(None, vids)) # WARNING - this filters vertex id 0 also
  vids = [vid for fid in fids for vid in [find_vertex_idx(graph.graph, fid)] if vid is not None ]
  if len(vids) <= 0:
    raise HTTPException(status_code=404, detail="Invalid fids")
  try:
    klists = []
    mindist_and_order = min_degree
    limit = max_neighbors
    while mindist_and_order <= max_degree:
        neighbors = graph.graph.neighborhood(
            vids, order=mindist_and_order, mode="out", mindist=mindist_and_order
        )
        # TODO prune the graph after sorting by edge weight
        klists.append(graph.graph.vs[neighbors[0][:limit]]["name"])
        limit = limit - len(neighbors[0])
        if limit <= 0:
            break # we have reached limit of neighbors
        mindist_and_order += 1
    # end of while
    return list(itertools.chain(*klists))
  except ValueError:
    raise HTTPException(status_code=404, detail="Neighbors not found")

async def _get_direct_edges_df(  
  fids: list[int],
  graph: Graph,        
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> pandas.DataFrame: 
  # WARNING we are operating on a shared dataframe...
  # ...inplace=False by default, explicitly setting here for emphasis
  out_df = graph.df[graph.df['i'].isin(fids)].sort_values(by=['v'], ascending=False, inplace=False)[:max_neighbors]
  return out_df

async def get_direct_edges_list(  
  fids: list[int],
  graph: Graph,        
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> pandas.DataFrame: 
  start_time = time.perf_counter()
  out_df = await _get_direct_edges_df(fids, graph, max_neighbors)
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs for {len(out_df)} direct edges")
  return out_df[['j','v']].to_dict('records')
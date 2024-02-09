from typing import Annotated
import itertools
import time

import pandas

import igraph
from loguru import logger
from fastapi import Request, Query, HTTPException

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
  logger.info(f"graph took {time.perf_counter() - start_time} secs")
  logger.debug(neighbors)
  start_time = time.perf_counter()
  res = graph.df[graph.df['i'].isin(neighbors) & graph.df['j'].isin(neighbors)]
  logger.info(f"dataframe took {time.perf_counter() - start_time} secs")
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
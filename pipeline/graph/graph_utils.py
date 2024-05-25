import time

import go_eigentrust

import pandas as pd
import igraph as ig
from loguru import logger

def get_direct_edges_df(  
  fid: int,
  df: pd.DataFrame,        
  max_neighbors: int,
) -> pd.DataFrame: 
  # WARNING we are operating on a shared dataframe...
  # ...inplace=False by default, explicitly setting here for emphasis
  out_df = df[df['i'] == fid].sort_values(by=['v'], ascending=False, inplace=False)[:max_neighbors]
  return out_df

def get_k_degree_neighbors(
  fid: int,
  graph: ig.Graph,      
  limit: int,
  k: int, 
  process_label: str
) -> list[int]:
  start_time  = time.perf_counter()
  try:
    vid = graph.vs.find(name=fid).index
  except:
    logger.error(f"{process_label}| {fid} NOT FOUND in graph. Skipping.")
    return []
  neighbors = graph.neighborhood(vid, order=k, mode="out", mindist=k)
  if len(neighbors) > 0:
    k_neighbors_list = graph.vs[neighbors[:limit]]["name"]
    return k_neighbors_list
  return []

def get_k_degree_scores(
  fid: int,
  k_minus_list: list[int],
  df: pd.DataFrame,
  graph: ig.Graph,      
  limit: int,
  k: int, 
  process_label: str
) -> list[int]:
  start_time = time.perf_counter()
  k_fid_list = get_k_degree_neighbors(fid, graph, limit, k, process_label)
  logger.debug(f"{process_label}| iGraph took {time.perf_counter() - start_time} secs"
                  f" for {len(k_fid_list)} k-{k} neighbors")
  if len(k_fid_list) > 0:
    # include all previous degree neighbors when calculating go-eigentrust
    k_fid_list.extend(k_minus_list)
    k_fid_list.extend([fid])
    logger.trace(f"{process_label}| k_fid_list:{k_fid_list}")

    start_time  = time.perf_counter()
    k_df = df.query('i in @k_fid_list').query('j in @k_fid_list')
    logger.debug(f"{process_label}| k-{k} Pandas took {time.perf_counter() - start_time} secs for {len(k_df)} edges")

    if len(k_df) > 0:
      k_scores = go_eigentrust.get_scores(k_df, [fid])
      # filter out previous degree neighbors
      k_scores = [ score for score in k_scores if score['i'] not in k_minus_list]
      return k_scores
  return []

  


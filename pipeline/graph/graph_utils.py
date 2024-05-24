import time

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
  log_label: str
) -> list[int]:
  start_time  = time.perf_counter()
  try:
    vid = graph.vs.find(name=fid).index
  except:
    logger.error(f"{log_label}| {fid} NOT FOUND in graph. Skipping.")
    return []
  neighbors = graph.neighborhood(vid, order=k, mode="out", mindist=k)
  logger.info(f"{log_label}| iGraph took {time.perf_counter() - start_time} secs for {len(neighbors)} neighbors")
  if len(neighbors) > 0:
    k_neighbors_list = graph.vs[neighbors[:limit]]["name"]
    return k_neighbors_list
  return []



        


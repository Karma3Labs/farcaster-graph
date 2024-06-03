import time
import gc

import go_eigentrust
import utils
from config import settings

import pandas as pd
import polars as pl
from loguru import logger
import niquests

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
  limit: int,
  k: int, 
) -> list[int]:
  payload = {'fid': int(fid), 'k': k, 'limit': limit}
  response = niquests.get(settings.PERSONAL_IGRAPH_URLPATH, params=payload)
  logger.trace(f"{response.json()}")
  return response.json()

def get_k_degree_scores(
  fid: int,
  k_minus_list: list[int],
  localtrust_df: pl.DataFrame,
  limit: int,
  k: int, 
  process_label: str
) -> list[int]:
  start_time = time.perf_counter()
  k_fid_list = get_k_degree_neighbors(
                                fid, 
                                limit, 
                                k)
  logger.debug(f"{process_label}iGraph took {time.perf_counter() - start_time} secs"
                  f" for {len(k_fid_list)} k-{k} neighbors")
  if len(k_fid_list) > 0:
    # include all previous degree neighbors when calculating go-eigentrust
    k_fid_list.extend(k_minus_list)
    k_fid_list.extend([fid])
    logger.trace(f"{process_label}k_fid_list:{k_fid_list}")

    start_time  = time.perf_counter()
    k_df = localtrust_df.filter((pl.col('i').is_in(k_fid_list)) &
                                (pl.col('j').is_in(k_fid_list)))

    logger.debug(f"{process_label}k-{k} Polars took {time.perf_counter() - start_time} secs for {len(k_df)} edges")

    if len(k_df) > 0:
      k_df_pd = k_df.to_pandas()
      k_scores = go_eigentrust.get_scores(k_df_pd, [fid])
      del k_df_pd
      
      # filter out previous degree neighbors
      k_scores = [ score for score in k_scores if score['i'] not in k_minus_list]

      return k_scores
  return []

  


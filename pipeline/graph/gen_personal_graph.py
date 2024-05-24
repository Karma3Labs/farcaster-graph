# standard dependencies
from pathlib import Path
import argparse
import multiprocessing as mp
from functools import partial
import time
import math
import os
import sys

# local dependencies
import utils
from config import settings
from . import graph_utils
import go_eigentrust

# 3rd party dependencies
import pandas as pd
import polars as pl
import igraph as ig
import numpy as np
import psutil 
from loguru import logger

def split_arr(
    fids: np.ndarray, 
    chunksize:int, 
):
  num_splits = math.ceil( len(fids) / chunksize )
  logger.info(f"Splitting fids list into {num_splits} splits")
  splits = np.array_split(fids, num_splits )
  logger.info(f"Number of splits: {len(splits)}")
  for idx, arr in enumerate(splits):
    # we need batch id for logging and debugging
    # yield a tuple because pool.map takes only 1 argument
    logger.info(f"Yield split# {idx}")
    yield (idx, arr)

def graph_fn(
    outdir:Path,
    maxneighbors:int,
    pd_df: pd.DataFrame, 
    graph: ig.Graph, 
    slice: tuple[int, pl.DataFrame]
):
  # because we are in a sub-process, 
  # ...we need to set log level again if we don't want defaults
  logger.remove()
  logger.add(sys.stderr, level=settings.LOG_LEVEL)

  slice_id = slice[0]
  slice_arr = slice[1]
  
  process = mp.current_process()
  process_label = f"| {process.pid} | {process.name} | SLICE#{slice_id}"
  logger.info(f"{process_label}| sample FIDs: {np.random.choice(slice_arr, size=min(5, len(slice)), replace=False)}")
  logger.info(f"{process_label}| {utils.df_info_to_string(pd_df, True)}")
  logger.info(f"{process_label}| {ig.summary(graph)}")

  pl_df = pl.DataFrame()
  for idx, fid in enumerate(slice_arr):
    logger.info(f"{process_label}| fid: {fid}")
    if(idx % 1e4 == 9999):
        pl_df = pl_df.rechunk() # make contiguous
    start_time = time.perf_counter()
    k1_df = graph_utils.get_direct_edges_df(fid, pd_df, maxneighbors)
    logger.info(f"{process_label}| k-1 neighbors took {time.perf_counter() - start_time} secs for {len(k1_df)} edges")

    k1_scores = go_eigentrust.get_scores(k1_df, [fid])
    logger.info(f"{process_label}| {fid}: 1st degree neigbors: {len(k1_scores)}")
    logger.trace(f"{process_label}| {fid}: 1st degree neigbors scores: {k1_scores}")

    pl_fid = pl.DataFrame(k1_scores, schema={"i": pl.UInt32, "v":pl.Float64}) \
                .with_columns(pl.lit(fid).alias("fid"), pl.lit(1).alias("degree"))
    logger.debug(f"{process_label}| pl_fid: {pl_fid.describe()}")
    pl_df = pl_df.vstack(pl_fid)

    logger.debug(f"{process_label}| pl_df: {pl_df.describe()}")
    limit = maxneighbors - len(k1_df)
    if limit > 0:
      start_time = time.perf_counter()
      k2_fid_list = graph_utils.get_k_degree_neighbors(fid, graph, limit, 2, process_label)
      logger.info(f"{process_label}| iGraph took {time.perf_counter() - start_time} secs"
                  f" for {len(k2_fid_list)} k-2 neighbors")
      if len(k2_fid_list) > 0:
        start_time  = time.perf_counter()
        k1_fid_list = k1_df['j'].to_list()
        k2_fid_list.extend(k1_fid_list)
        k2_fid_list.extend([fid])
        logger.debug(f"{process_label}| k2_fid_list:{k2_fid_list}")
        k2_df = pd_df.query('i in @k2_fid_list').query('j in @k2_fid_list')
        logger.info(f"{process_label}| k2_df took {time.perf_counter() - start_time} secs for {len(k2_df)} edges")

        if len(k2_df) > 0:
          k2_scores = go_eigentrust.get_scores(k2_df, [fid])
          # filter out 1st degree neighbors
          k2_scores = [ score for score in k2_scores if score['i'] not in k1_fid_list]
          logger.info(f"{process_label}| {fid}: 2nd degree neigbors: {len(k2_scores)}")
          logger.trace(f"{process_label}| {fid}: 2nd degree neigbors scores: {k2_scores}")

          pl_fid = pl.DataFrame(k2_scores, schema={"i": pl.UInt32, "v":pl.Float64}) \
                    .with_columns(pl.lit(fid).alias("fid"), pl.lit(2).alias("degree"))
          logger.debug(f"{process_label}| pl_fid: {pl_fid.describe()}")
          pl_df = pl_df.vstack(pl_fid)

  pl_df = pl_df.rechunk() # make contiguous
  logger.info(f"{process_label}| pl_df: {pl_df.describe()}")
  logger.info(f"{process_label}| pl_df sample: {pl_df.sample(n=5)}")

def main(
    inpkl:Path,  
    outdir:Path, 
    procs:int, 
    chunksize:int, 
    maxneighbors:int
):
  logger.info(f"Reading pickle {inpkl} into DataFrame")
  edges_df = pd.read_pickle(inpkl)
  logger.info(utils.df_info_to_string(edges_df, True))
  # graph = ig.Graph.DataFrame(edges_df, directed=True, use_vids=False)
  gfile = os.path.join(inpkl.parent, os.path.basename(inpkl).replace('_df.pkl', '_ig.pkl'))
  logger.info(f"Reading pickle {gfile} into iGraph")
  graph = ig.Graph.Read_Pickle(gfile)
  logger.info(ig.summary(graph))

  # we need to compute personalized ranking for every profile in Farcaster
  # ... let's extract all the fids that have had outgoing interactions.
  fids = pd.unique(edges_df['i'])
  np.random.shuffle(fids)
  logger.info(fids)

  logger.info(f"Physical Cores={psutil.cpu_count(logical=False)}")
  logger.info(f"Logical Cores={psutil.cpu_count(logical=True)}")
  logger.info(f"spawning {procs} processes")

  # pool.map takes only 1 argument but we need to send multiple arguments
  # let's create a partial function with the argument 
  # ...that is the same for every batch
  batch_fn = partial(graph_fn, outdir, maxneighbors, edges_df, graph)
  with mp.get_context('spawn').Pool(processes=procs) as pool:
    # split the fids into groups and spawn processes
    # WARNING: we don't use shared_memory so dataframe and graph will be copied to each process
    # TODO use shared_memory or joblib with sharedmem 
    pool.map(batch_fn, split_arr(fids, chunksize))

  logger.info("Done!")


# (.venv)$ python3 -m graph.gen_personal_graph -i ../serve/samples/fc_engagement_fid_df.pkl -o /tmp -p 2 -c 3
if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--inpkl",
                      help="input localtrust pickle file",
                      required=True,
                      type=lambda f: Path(f).expanduser().resolve())  
  parser.add_argument("-o", "--outdir",
                    help="output directory",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())
  parser.add_argument("-p", "--procs",
                    help="number of processes to kick off",
                    required=True,
                    type=int)
  parser.add_argument("-c", "--chunksize",
                    help="number of fids in each chunk",
                    required=True,
                    type=int)
  parser.add_argument("-m", "--maxneighbors",
                    help="max number of neighbors",
                    required=True,
                    type=int)
  args = parser.parse_args()
  print(args)

  main(inpkl=args.inpkl, 
       outdir=args.outdir, 
       procs=args.procs, 
       chunksize=args.chunksize, 
       maxneighbors=args.maxneighbors)
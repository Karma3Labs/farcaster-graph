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
    logger.info(f"{process_label}| processing FID: {fid}")
    if(idx % 1e4 == 9999):
        start_time = time.perf_counter()
        pl_df = pl_df.rechunk() # make contiguous
        logger.info(f"{process_label}| rechunk took {time.perf_counter() - start_time} secs")
    k_minus_list = []
    limit = maxneighbors
    degree = 1
    while limit > 0 and degree <= 5:
      start_time = time.perf_counter()
      k_scores = graph_utils.get_k_degree_scores(fid, k_minus_list, pd_df, graph, limit, degree, process_label)
      logger.trace(f"{process_label}| FID {fid}: {degree}-degree neigbors scores: {k_scores}")
      if len(k_scores) == 0:
        logger.info(f"{process_label}| k-{degree} took {time.perf_counter() - start_time} secs"
              f" for {len(k_scores)} neighbors"
              f" for FID {fid}")
        break
      row = {"fid":fid, "degree":degree, "scores": [k_scores]}
      pl_fid = pl.DataFrame(row, schema={'fid': pl.UInt32, 'degree': pl.UInt8, 'scores': pl.List})
      logger.debug(f"{process_label}| pl_fid: {pl_fid.describe()}")
      pl_df = pl_df.vstack(pl_fid)
      logger.info(f"{process_label}| k-{degree} took {time.perf_counter() - start_time} secs"
                    f" for {len(k_scores)} neighbors"
                    f" for FID {fid}")
      logger.debug(f"{process_label}| pl_df: {pl_df.describe()}")
      k_minus_list = [ score['i'] for score in k_scores ]
      limit = limit - len(k_scores)
      degree = degree + 1
      utils.log_memusage(logger)
    # end while
  # end for loop

  start_time = time.perf_counter()
  pl_df = pl_df.rechunk() # make contiguous
  logger.info(f"{process_label}| rechunk took {time.perf_counter() - start_time} secs")
  utils.log_memusage(logger)

  logger.info(f"{process_label}| pl_df: {pl_df.describe()}")
  logger.info(f"{process_label}| pl_df sample: {pl_df.sample(n=min(5, len(pl_df)))}")

  outfile = os.path.join(outdir, f"{slice_id}.pqt")
  logger.info(f"{process_label}| writing output to {outfile}")
  start_time = time.perf_counter()
  pl_df.write_parquet(file=outfile, compression='lz4', use_pyarrow=True)
  logger.info(f"{process_label}| writing to {outfile} took {time.perf_counter() - start_time} secs")

  return slice_id

def success_callback(slice_id):
  logger.info(f"SUCCESS: {slice_id} completed successfully")

def error_callback(err):
  logger.info(err)

def main(
    inpkl:Path,  
    outdir:Path, 
    procs:int, 
    chunksize:int, 
    maxneighbors:int
):
  logger.info(f"Reading pickle {inpkl} into DataFrame")
  utils.log_memusage(logger)
  edges_df = pd.read_pickle(inpkl)
  logger.info(utils.df_info_to_string(edges_df, True))
  utils.log_memusage(logger)
  # graph = ig.Graph.DataFrame(edges_df, directed=True, use_vids=False)
  gfile = os.path.join(inpkl.parent, os.path.basename(inpkl).replace('_df.pkl', '_ig.pkl'))
  logger.info(f"Reading pickle {gfile} into iGraph")
  graph = ig.Graph.Read_Pickle(gfile)
  logger.info(ig.summary(graph))
  utils.log_memusage(logger)

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
  pool = mp.get_context('spawn').Pool(processes=procs)
  pool.map_async(batch_fn, 
                  split_arr(fids, chunksize), 
                  callback=success_callback, 
                  error_callback=error_callback)
  pool.close()
  pool.join()
  # with mp.get_context('spawn').Pool(processes=procs) as pool:
  #   # split the fids into groups and spawn processes
  #   # WARNING: we don't use shared_memory so dataframe and graph will be copied to each process
  #   # TODO use shared_memory or joblib with sharedmem 
  #   pool.map_async(batch_fn, 
  #                  split_arr(fids, chunksize), 
  #                  callback=success_callback, 
  #                  error_callback=error_callback)

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
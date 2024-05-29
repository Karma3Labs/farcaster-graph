# standard dependencies
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import time
import math
import os
import sys
import asyncio
import gc

# local dependencies
import utils
from config import settings
from . import graph_utils

# 3rd party dependencies
import polars as pl
import numpy as np
import psutil 
from loguru import logger

def flatten_list_of_lists(list_of_lists):
  flat_list = []
  for nested_list in list_of_lists:
      flat_list.extend(nested_list)
  return flat_list

def yield_pl_slices(
    fids: pl.DataFrame, 
    chunksize:int, 
) :
  for idx, slice in enumerate(fids.iter_slices(n_rows=chunksize)):
    # we need batch id for logging and debugging
    # yield a tuple because pool.map takes only 1 argument
    logger.info(f"Yield split# {idx}")
    yield (idx, slice)

def yield_np_slices(
    fids: np.ndarray, 
    chunksize:int, 
) :
  num_slices = math.ceil( len(fids) / chunksize )
  logger.info(f"Slicing fids list into {num_slices} slices")
  slices = np.array_split(fids, num_slices )
  logger.info(f"Number of slices: {len(slices)}")
  for idx, arr in enumerate(slices):
    # we need batch id for logging and debugging
    # yield a tuple because pool.map takes only 1 argument
    logger.info(f"Yield split# {idx}")
    yield (idx, arr)

async def compute_task(
    fid: int,
    maxneighbors: int,
    localtrust_df: pl.DataFrame, 
    process_label: str
) -> list:
  try:
    logger.info(f"{process_label}processing FID: {fid}")
    task_start = time.perf_counter()
    knn_list = []
    k_minus_list = []
    limit = maxneighbors
    degree = 1
    while limit > 0 and degree <= 5:
      start_time = time.perf_counter()
      k_scores = graph_utils.get_k_degree_scores(
                                        fid, 
                                        k_minus_list, 
                                        localtrust_df, 
                                        limit, 
                                        degree, 
                                        process_label)
      logger.info(f"{process_label}k-{degree} took {time.perf_counter() - start_time} secs"
                  f" for {len(k_scores)} neighbors"
                  f" for FID {fid}")
      logger.trace(f"{process_label}FID {fid}: {degree}-degree neigbors scores: {k_scores}")
      if len(k_scores) == 0:
        break
      row = {"fid":fid, "degree":degree, "scores": k_scores}
      knn_list.append(row)
      k_minus_list.extend([ score['i'] for score in k_scores ])
      limit = limit - len(k_scores)
      degree = degree + 1
    # end while
    logger.info(f"{process_label}FID {fid} task took {time.perf_counter() - task_start} secs")
    return knn_list
  except:
    logger.error(f"{process_label}"
                 f"fid:{fid}"
                 f"degree:{degree}"
                 f"limit:{limit}")
    logger.exception(f"{process_label}")
  return []

async def compute_tasks_concurrently(
    maxneighbors:int,
    localtrust_df: pl.DataFrame, 
    slice: np.ndarray,
    process_label: str
) -> list:
  try:
    tasks = []
    for fid in slice:
      tasks.append(asyncio.create_task(
                            compute_task(
                              fid=fid, 
                              maxneighbors=maxneighbors, 
                              localtrust_df=localtrust_df, 
                              process_label=process_label)))
    logger.info(f"{process_label}{len(tasks)} tasks created") 
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
  except:
    logger.exception(f"{process_label}")
  return []

def compute_subprocess(
  outdir:Path,
  maxneighbors:int,
  localtrust_df: pl.DataFrame, 
  slice: tuple[int, np.ndarray]
):
  # because we are in a sub-process, 
  # ...we need to set log level again if we don't want defaults
  logger.remove()
  logger.add(sys.stderr, level=settings.LOG_LEVEL)

  slice_id = slice[0]
  slice_arr = slice[1]
  pid = os.getpid()
  process_label = f"| {pid} | SLICE#{slice_id}| "
  logger.info(f"{process_label}size of FIDs slice: {len(slice_arr)}")
  logger.info(f"{process_label}sample of FIDs slice: {np.random.choice(slice_arr, size=min(5, len(slice)), replace=False)}")
  results = [result for result in asyncio.run(
                                      compute_tasks_concurrently(
                                        maxneighbors, 
                                        localtrust_df, 
                                        slice_arr, 
                                        process_label))]
  
  results = flatten_list_of_lists(results)
  logger.info(f"{process_label}{len(results)} results available")

  # pl_slice = pl.DataFrame(results, schema={'fid': pl.UInt32, 'degree': pl.UInt8, 'scores': pl.List})
  # del results
  pl_slice = pl.LazyFrame(results, schema={'fid': pl.UInt32, 'degree': pl.UInt8, 'scores': pl.List})
  
  logger.info(f"{process_label}pl_slice: {pl_slice.describe()}")
  # logger.info(f"{process_label}pl_slice sample: {pl_slice.sample(n=min(5, len(pl_slice)))}")

  outfile = os.path.join(outdir, f"{slice_id}.pqt")
  logger.info(f"{process_label}writing output to {outfile}")
  start_time = time.perf_counter()

  # pl_slice.write_parquet(file=outfile, compression='lz4', use_pyarrow=True)
  # del pl_slice
  pl_slice.sink_parquet(path=outfile, compression='lz4')
  del results

  utils.log_memusage(logger, prefix=process_label + 'before subprocess gc ')
  gc.collect()
  utils.log_memusage(logger, prefix=process_label + 'after subprocess gc ')


  logger.info(f"{process_label}writing to {outfile} took {time.perf_counter() - start_time} secs")
  return slice_id


async def main(
    incsv:Path,  
    outdir:Path, 
    procs:int, 
    chunksize:int, 
    maxneighbors:int
):
  start_time = time.perf_counter()
  logger.info(f"Reading csv {incsv} into Polars DataFrame")
  utils.log_memusage(logger)
  edges_df = pl.read_csv(incsv)
  logger.info(f"edges_df: {edges_df.describe()}")
  logger.info(f"edges_df sample: {edges_df.sample(n=min(5, len(edges_df)))}")
  utils.log_memusage(logger)

  # logger.info(f"Reading pickle {inpkl} into DataFrame")
  # utils.log_memusage(logger)
  # edges_df = pd.read_pickle(inpkl)
  # logger.info(utils.df_info_to_string(edges_df, True))
  # utils.log_memusage(logger)

  # we need to compute personalized ranking for every profile in Farcaster
  # ... let's extract all the fids that have had outgoing interactions.
  fids = edges_df.select(pl.col('i')).unique().to_numpy().flat
  # fids = pd.unique(edges_df['i'])
  fids = np.random.choice(fids, size=len(fids), replace=False)
  # np.random.shuffle(fids) # does not work with Polars because read-only
  
  logger.info(np.random.choice(fids, min(len(fids), 5)))

  logger.info(f"Physical Cores={psutil.cpu_count(logical=False)}")
  logger.info(f"Logical Cores={psutil.cpu_count(logical=True)}")
  logger.info(f"spawning {procs} processes")

  # on Linux default MP method is fork which is not compatible with Polars
  mp.set_start_method("spawn")
  loop = asyncio.get_running_loop()

  # WARNING: Do NOT use max_tasks_per_child. It will kill sub-processes
  with ProcessPoolExecutor(max_workers=procs) as executor:
    tasks = [loop.run_in_executor(executor, 
                                  compute_subprocess, 
                                  outdir,
                                  maxneighbors,
                                  edges_df, 
                                  slice)
              for slice in yield_np_slices(fids, chunksize)]
    # results = [result for sub_list in await asyncio.gather(*tasks) for result in sub_list]
    results = [result for result in await asyncio.gather(*tasks, return_exceptions=True)]

  logger.info(f"Total run time: {time.perf_counter() - start_time:.2f} second(s)")
  logger.info("Done!")


# (.venv)$ python3 -m graph.gen_personal_graph -i ../serve/samples/fc_engagement_fid_df.pkl -o /tmp -p 2 -c 3
if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--incsv",
                      help="input localtrust csv file",
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

  asyncio.run(
    main(
      incsv=args.incsv, 
      outdir=args.outdir, 
      procs=args.procs, 
      chunksize=args.chunksize, 
      maxneighbors=args.maxneighbors))
# standard dependencies
from pathlib import Path
import argparse
import logging
import multiprocessing as mp
from functools import partial
import time
import random

# local dependencies
import utils

# 3rd party dependencies
import pandas as pd
import polars as pl
import igraph as ig
import psutil 

def graph_fn(pd_df: pd.DataFrame, pl_df: pl.LazyFrame, graph: ig.GraphBase, slice: tuple[int, pl.DataFrame]):
  logger = mp.get_logger()
  logger.handlers.clear() 
  logger.setLevel(logging.DEBUG)
  # add handler otherwise nothing will print to console
  # ... but adding a handler results in duplicate handler
  # ... so clear existing handlers and then add
  utils.setup_consolelogger(logger)  
  slice_id = slice[0]
  slice_df = slice[1]
  process = mp.current_process()
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | {slice_df.glimpse}")
  # logger.info(f"{process.name} | SLICE#{slice_id} | {pl_df.describe()}") # WARN: potentially expensive operation
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | {pl_df.schema}")
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | {utils.df_info_to_string(pd_df, True)}")
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | {ig.summary(graph)}")
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | sleepy")
  time.sleep(random.randint(1,10))
  logger.info(f"{process.pid} | {process.name} | SLICE#{slice_id} | awake")

def split_df(df: pl.DataFrame):
  for idx, frame in enumerate(df.iter_slices(n_rows=2)):
    # we need batch id for logging and debugging
    # yield a tuple because pool.map takes only 1 argument
    yield (idx, frame)

def main(incsv:Path,  outdir:Path, procs:int, logger:logging.Logger):
  edges_df = pd.read_csv(incsv)
  lazy_df = pl.scan_csv(incsv)
  graph = ig.Graph.DataFrame(edges_df, directed=True, use_vids=False)
  # logger.info(lazy_df.describe()) # WARN: potentially expensive operation
  logger.info(lazy_df.schema)
  logger.info(utils.df_info_to_string(edges_df, True))
  logger.info(ig.summary(graph))

  # we need to compute personalized ranking for every profile in Farcaster
  # ... let's extract all the fids that have had outgoing interactions.
  fid_df = lazy_df.select(
    [ 
     pl.col('i').unique().alias('unique_fid')
    ]
  ).collect()

  logger.info(f"Physical Cores={psutil.cpu_count(logical=False)}")
  logger.info(f"Logical Cores={psutil.cpu_count(logical=True)}")
  logger.info(f"spawning {procs} processes")

  # pool.map takes only 1 argument but we need to send multiple arguments
  # let's create a partial function with the argument 
  # ...that is the same for every batch
  batch_fn = partial(graph_fn, edges_df, lazy_df, graph)
  with mp.get_context('spawn').Pool(processes=procs) as pool:
    # split the fids into groups and spawn processes
    pool.map(batch_fn, split_df(fid_df))

  logger.info("Done!")




# (.venv)$ python3 -m graph.pre_compute_personal -i ../serve/samples/lt_l1rep6rec3m12enhancedConnections_fid.csv -o /tmp -p 2
if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--incsv",
                      help="input localtrust csv file",
                      required=True,
                      type=lambda f: Path(f).expanduser().resolve())  
  parser.add_argument("-o", "--outdir",
                    help="output directory for pickle files",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())
  parser.add_argument("-p", "--procs",
                    help="number of processes to kick off",
                    required=True,
                    type=int)
  args = parser.parse_args()
  print(args)

  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  main(incsv=args.incsv, outdir=args.outdir, procs=args.procs, logger=logger)
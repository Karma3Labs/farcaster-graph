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
import polars as pl
import psutil 

def graph_fn(df: pl.LazyFrame, slice: tuple[int, pl.DataFrame]):
  logger = mp.get_logger()
  logger.handlers.clear() 
  logger.setLevel(logging.DEBUG)
  # add handler otherwise nothing prints
  # ... but adding handler results in duplicate handler
  # ... so clear existing handlers and then add
  utils.setup_consolelogger(logger)  
  slice_id = slice[0]
  slice_df = slice[1]
  process = mp.current_process()
  logger.info(f"{process.name} | SLICE#{slice_id} | {slice_df.glimpse}")
  time.sleep(random.randint(1,10))
  logger.info(f"{process.name} | SLICE#{slice_id} | {df.describe()}")

def split_df(df: pl.DataFrame):
  for idx, frame in enumerate(df.iter_slices(n_rows=2)):
    yield (idx, frame)

def main(incsv:Path,  outdir:Path, procs:int, logger:logging.Logger):
  lazy_df = pl.scan_csv(incsv)
  # logger.info(lazy_df.describe()) # WARN: potentially expensive operation
  logger.info(lazy_df.schema)

  fid_df = lazy_df.select(
    [
     pl.col('i').unique().alias('unique_fid')
    ]
  ).collect()

  logger.info(f"Physical Cores={psutil.cpu_count(logical=False)}")
  logger.info(f"Logical Cores={psutil.cpu_count(logical=True)}")
  logger.info(f"spawning {procs} processes")

  batch_fn = partial(graph_fn, lazy_df)
  with mp.get_context('spawn').Pool(processes=procs) as pool:
    pool.map(batch_fn, split_df(fid_df))

  logger.info("Done!")

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
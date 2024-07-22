from pathlib import Path
import argparse
import math
import json

import polars as pl
import pandas as pd
import numpy as np
from loguru import logger

import utils

def fetch_fids_edges_from_csv(incsv: Path) -> tuple[list[str], pl.DataFrame]:
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

  logger.info("sort edges_df")
  edges_df =  edges_df.sort(['i', 'j'])

  return fids, edges_df

def fetch_edges_df_from_pkl(inpkl: Path) -> pl.DataFrame:
  # Load the pickle file into a Pandas DataFrame
  pandas_df = pd.read_pickle(inpkl)

  # Convert the Pandas DataFrame to a Polars DataFrame
  polars_df = pl.from_pandas(pandas_df)

  return polars_df


# def fetch_fids_from_csv(incsv: Path) -> tuple[np.ndarray, pl.DataFrame]:
#   fids, _ = fetch_fids_edges_from_csv(incsv)

#   # print fids to pass in as a XCom push variable for Airflow job so that the
#   # next task can take in fids as a parameter.
#   print(','.join(map(str, fids)))
#   return fids

def fetch_and_slice_fids(incsv: Path, chunksize: int, outdir: Path) -> list[list[int]]:
  fids, edges_df = fetch_fids_edges_from_csv(incsv)

  num_slices = math.ceil( len(fids) / chunksize )
  logger.info(f"Slicing fids list into {num_slices} slices")
  slices = np.array_split(fids, num_slices )
  logger.info(f"Number of slices: {len(slices)}")
  res = []
  for idx, arr in enumerate(slices):
    # we need batch id for logging and debugging
    # yield a tuple because pool.map takes only 1 argument
    # logger.info(f"Yield split# {idx}: {arr}")
    res.append(arr.tolist())
    # yield (idx, arr)

  out_edges_df_path = f"{outdir}/edges_df.pkl"
  edges_df.to_pandas().to_pickle(out_edges_df_path)
  logger.info(f'wrote to {out_edges_df_path}')

  # KEEP this print line at the last so that Airflow dag can load the fids from the log file from airflow.
  print(res)

  return arr

if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--incsv",
                      help="input localtrust csv file",
                      required=True,
                      type=lambda f: Path(f).expanduser().resolve())
  parser.add_argument("-c", "--chunksize",
                    help="number of fids in each chunk",
                    required=True,
                    type=int)
  parser.add_argument("-o", "--out",
                    help="output to save chunks and pkl file",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())


  args = parser.parse_args()
  print(args)

  fetch_and_slice_fids(incsv=args.incsv, chunksize=args.chunksize, outdir=args.out)
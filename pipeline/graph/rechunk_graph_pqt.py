# standard dependencies
from pathlib import Path
import argparse
import sys
import os

# local dependencies
from config import settings

# 3rd party dependencies
from loguru import logger
import polars as pl

def main(indir:Path, outfile:Path):
  pq_df = pl.read_parquet(f"{indir}/*.pqt", rechunk=True, low_memory=False)
  logger.info(f"df estimated_size: {pq_df.estimated_size('mb')}")
  logger.info(f"df describe: {pq_df.describe()}")
  logger.info(f"df sample: {pq_df.sample(n=min(5, len(pq_df)))}")
  
  pq_df.write_parquet(outfile, 
                      use_pyarrow=True, 
                      statistics=True,
                      pyarrow_options={
                        "write_statistics": True,
                        "row_group_size": 100_000})

  # import pyarrow as pa
  # import pyarrow.dataset as ds
  # ds.write_dataset(
  #       pq_df.to_arrow(),
  #       outdir,
  #       format="parquet",
  #       min_rows_per_group=100_000,
  #       max_rows_per_group=100_000,
  #       partitioning=ds.partitioning(pa.schema([("i", pa.uint32())])),
  #       existing_data_behavior="overwrite_or_ignore"
  #   )
  
  pass

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--indir",
                    help="input directory with all pqt files",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())  
  parser.add_argument("-o", "--outfile",
                    help="output filename",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())
    
  args = parser.parse_args()
  print(args)

  logger.remove()
  logger.add(sys.stderr, level=settings.LOG_LEVEL)

  if os.path.isdir(args.outfile):
    logger.error("-o / --outfile should be a file not a directory")
    sys.exit(1)
  main(args.indir, args.outfile)
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

def main(indir: Path, outfile: Path):

    logger.info(f"reading parquet files {indir}/*.pqt")
    pq_files = [os.path.join(indir, f) for f in os.listdir(indir) if f.endswith('.pqt')]
    if not pq_files:
        raise FileNotFoundError(f"No parquet files found in {indir}")

    # Read all parquet files into a list of DataFrames
    dfs = []
    for file in pq_files:
        try:
            df = pl.read_parquet(file, rechunk=True, low_memory=False)
            dfs.append(df)
            logger.debug(f"Successfully read {file}")
        except Exception as e:
            logger.error(f"Error reading {file}: {e}")

    if not dfs:
        raise ValueError("No valid parquet files could be read")

    # Concatenate all DataFrames into a single DataFrame
    pq_df = pl.concat(dfs)

    logger.info(f"df estimated_size: {pq_df.estimated_size('mb')}")
    logger.info(f"df describe: {pq_df.describe()}")
    logger.info(f"df sample: {pq_df.sample(n=min(5, len(pq_df)))}")

    logger.info(f"writing to parquet file {outfile}")
    pq_df.write_parquet(outfile,
                        use_pyarrow=True,
                        statistics=True,
                        pyarrow_options={
                          "write_statistics": True,
                          "row_group_size": 100_000})

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
    logger.add(sys.stderr, level='INFO')

    if os.path.isdir(args.outfile):
        logger.error("-o / --outfile should be a file not a directory")
        sys.exit(1)
    main(args.indir, args.outfile)

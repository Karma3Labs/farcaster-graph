# standard dependencies
from pathlib import Path
import argparse
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
from .fetch_nodes_edges import fetch_fids_edges_from_csv, fetch_edges_df_from_pkl
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

def yield_np_slices(fids: np.ndarray, chunksize: int):
    num_slices = math.ceil(len(fids) / chunksize)
    logger.info(f"Slicing fids list into {num_slices} slices")
    slices = np.array_split(fids, num_slices)
    logger.info(f"Number of slices: {len(slices)}")
    for idx, arr in enumerate(slices):
        # we need batch id for logging and debugging
        logger.info(f"Yield split# {idx}")
        yield (idx, arr)

async def compute_task(fid: int, maxneighbors: int, localtrust_df: pl.DataFrame, process_label: str) -> list:
    try:
        logger.info(f"{process_label}processing FID: {fid}")
        task_start = time.perf_counter()
        knn_list = []
        # NOTE: k_minus_list is empty because we want 1st degree neighbors to include input fid.
        # This is useful when creating watchlists of whale fids.
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
                process_label
            )
            logger.info(f"{process_label}k-{degree} took {time.perf_counter() - start_time} secs"
                        f" for {len(k_scores)} neighbors"
                        f" for FID {fid}")
            logger.trace(f"{process_label}FID {fid}: {degree}-degree neighbors scores: {k_scores}")
            if len(k_scores) == 0:
                break
            row = {"fid": fid, "degree": degree, "scores": k_scores}
            knn_list.append(row)
            k_minus_list.extend([score['i'] for score in k_scores])
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

async def compute_tasks_concurrently(maxneighbors: int, localtrust_df: pl.DataFrame, slice: np.ndarray, process_label: str) -> list:
    try:
        tasks = []
        for fid in slice:
            tasks.append(asyncio.create_task(
                compute_task(
                    fid=fid,
                    maxneighbors=maxneighbors,
                    localtrust_df=localtrust_df,
                    process_label=process_label
                )))
        logger.info(f"{process_label}{len(tasks)} tasks created")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except:
        logger.exception(f"{process_label}")
    return []

async def compute_slice(outdir: Path, maxneighbors: int, localtrust_df: pl.DataFrame, slice: tuple[int, np.ndarray], semaphore: asyncio.Semaphore):
    async with semaphore:
        subprocess_start = time.perf_counter()
        slice_id = slice[0]
        slice_arr = slice[1]
        process_label = f"| SLICE#{slice_id}| "
        logger.info(f"{process_label}size of FIDs slice: {len(slice_arr)}")
        logger.info(f"{process_label}sample of FIDs slice: {np.random.choice(slice_arr, size=min(5, len(slice)), replace=False)}")
        results = [result for result in await compute_tasks_concurrently(
            maxneighbors,
            localtrust_df,
            slice_arr,
            process_label)]

        results = flatten_list_of_lists(results)
        logger.info(f"{process_label}{len(results)} results available")

        pl_slice = pl.LazyFrame(results, schema={'fid': pl.UInt32, 'degree': pl.UInt8, 'scores': pl.List})

        logger.info(f"{process_label}pl_slice: {pl_slice.describe()}")

        now = int(time.time())
        outfile = os.path.join(outdir, f"{slice_id}_{now}.pqt")
        logger.info(f"{process_label}writing output to {outfile}")
        start_time = time.perf_counter()

        pl_slice.sink_parquet(path=outfile, compression='lz4')
        del results

        utils.log_memusage(logger, prefix=process_label + 'before gc ')
        gc.collect()
        utils.log_memusage(logger, prefix=process_label + 'after gc ')

        logger.info(f"{process_label}writing to {outfile} took {time.perf_counter() - start_time} secs")
        logger.info(f"{process_label} slice computation took {time.perf_counter() - subprocess_start} secs")
        return slice_id

async def main(inpkl: Path, outdir: Path, procs: int, chunksize: int, maxneighbors: int, fids_str: str):
    start_time = time.perf_counter()

    fids = np.array(list(map(int, fids_str.split(','))))
    logger.info(f"Loaded {fids}")

    logger.info(f"Loading pkl {inpkl} into Polars DataFrame")
    edges_df = fetch_edges_df_from_pkl(inpkl)
    utils.log_memusage(logger)

    logger.info(f"Physical Cores={psutil.cpu_count(logical=False)}")
    logger.info(f"Logical Cores={psutil.cpu_count(logical=True)}")
    logger.info(f"Running {procs} slices concurrently")

    semaphore = asyncio.Semaphore(procs)

    # Run slices concurrently with the specified limit
    tasks = []
    for slice in yield_np_slices(fids, chunksize):
        tasks.append(compute_slice(outdir, maxneighbors, edges_df, slice, semaphore))

    await asyncio.gather(*tasks)

    logger.info(f"Total run time: {time.perf_counter() - start_time:.2f} second(s)")
    logger.info("Done!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inpkl",
                        help="input localtrust pkl file",
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
    parser.add_argument("-f", "--fids",
                        help="comma separated fids to process. eg) 1,2,3,420,69",
                        required=True,
                        type=str)
    args = parser.parse_args()
    print(args)

    asyncio.run(
        main(
            inpkl=args.inpkl,
            outdir=args.outdir,
            procs=args.procs,
            chunksize=args.chunksize,
            maxneighbors=args.maxneighbors,
            fids_str=args.fids,
        ))

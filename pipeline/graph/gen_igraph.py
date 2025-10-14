# standard dependencies
import argparse
import logging
import os
from pathlib import Path

# 3rd party dependencies
import igraph as ig
import pandas as pd

# local dependencies
import utils
from config import settings
from timer import Timer


@Timer(name="main")
def main(
    incsv: Path, outdir: Path, prefix: str, logger: logging.Logger, filtercsv: Path
):
    utils.log_memusage(logger)

    with Timer(name="read_csv"):
        logger.info(f"Reading CSV: {incsv}")
        edges_df = pd.read_csv(incsv, usecols=["i", "j", "v"])
        # DF is already indexed by i. Setting multi-index is not worth it.
        # edges_df.set_index(['i', 'j'])
    logger.info(utils.df_info_to_string(edges_df, with_sample=True))
    utils.log_memusage(logger)

    if filtercsv is not None:
        logger.info(f"Reading filter CSV: {filtercsv}")
        filter_df = pd.read_csv(filtercsv)
        filter_col_name = filter_df.columns[0]
        logger.info(utils.df_info_to_string(filter_df, with_sample=True))
        with Timer(name="filter_i"):
            logger.info(f"Filtering i on {filter_col_name}")
            edges_df = pd.merge(
                edges_df,
                filter_df,
                left_on=["i"],
                how="left",
                right_on=[filter_col_name],
            )
            edges_df = edges_df[edges_df[filter_col_name].notna()]
            edges_df = edges_df.drop(columns=[filter_col_name])
            logger.info(utils.df_info_to_string(edges_df, with_sample=True))
        with Timer(name="filter_j"):
            logger.info(f"Filtering j on {filter_col_name}")
            edges_df = pd.merge(
                edges_df,
                filter_df,
                left_on=["j"],
                how="left",
                right_on=[filter_col_name],
            )
            edges_df = edges_df[edges_df[filter_col_name].notna()]
            edges_df = edges_df.drop(columns=[filter_col_name])
            logger.info(utils.df_info_to_string(edges_df, with_sample=True))
        utils.log_memusage(logger)

    with Timer(name="df_to_igraph"):
        logger.info("Converting to igraph")
        g = ig.Graph.DataFrame(edges_df, directed=True, use_vids=False)
    logger.info(ig.summary(g))
    utils.log_memusage(logger)

    with Timer(name="write_pickle"):
        dfile = os.path.join(outdir, f"{prefix}_df.pkl")
        gfile = os.path.join(outdir, f"{prefix}_ig.pkl")
        logger.info(f"Saving dataframe to {dfile}")
        edges_df.to_pickle(dfile)
        logger.info(f"Saving igraph to {gfile}")
        g.write_pickle(gfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--incsv",
        help="input localtrust csv file",
        required=True,
        type=lambda f: Path(f).expanduser().resolve(),
    )
    parser.add_argument(
        "-o",
        "--outdir",
        help="output directory for pickle files",
        required=True,
        type=lambda f: Path(f).expanduser().resolve(),
    )
    parser.add_argument(
        "-p", "--prefix", help="file prefixes for pickle files", required=True, type=str
    )
    parser.add_argument(
        "-f",
        "--filtercsv",
        help="csv file with list of fids to filter the graph on",
        required=False,
        type=lambda f: Path(f).expanduser().resolve(),
    )
    args = parser.parse_args()
    print(args)
    print(settings)

    logger = logging.getLogger()
    utils.setup_filelogger(logger, __file__)
    logger.setLevel(logging.DEBUG)
    utils.setup_console_logger(logger)

    filtercsv = getattr(args, "filtercsv", None)

    main(
        incsv=args.incsv,
        outdir=args.outdir,
        prefix=args.prefix,
        logger=logger,
        filtercsv=filtercsv,
    )

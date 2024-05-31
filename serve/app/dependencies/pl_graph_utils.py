import time

from ..models.graph_model import PlGraph, GraphType

from fastapi import Request
import polars as pl
from loguru import logger


def get_engagement_graph(request: Request) -> PlGraph:
    return request.state.graph


async def get_neighbors_scores(
    fid: int,
    graph: PlGraph,
    max_degree: int,
    max_neighbors: int,
) -> list[dict]:
    """
    Sample dataframe
    ┌─────┬────────┬─────────────────────────────────┐
    │ fid ┆ degree ┆ scores                          │
    │ --- ┆ ---    ┆ ---                             │
    │ u32 ┆ u8     ┆ list[struct[2]]                 │
    ╞═════╪════════╪═════════════════════════════════╡
    │ 2   ┆ 1      ┆ [{2,0.625}, {19815,0.002486}, … │
    │ 3   ┆ 1      ┆ [{3,0.625}, {13683,0.00046}, …… │
    │ 4   ┆ 1      ┆ [{4,0.625}, {65,0.001109}, … {… │
    │ 5   ┆ 1      ┆ [{5,0.683453}, {404,0.006793},… │
    │ 5   ┆ 2      ┆ [{4959,0.00002}, {701,0.000029… │
    │ 6   ┆ 1      ┆ [{6,0.625}, {4606,0.043919}, …… │
    │ 7   ┆ 1      ┆ [{7,0.729625}, {34,0.0193125},… │
    │ 8   ┆ 1      ┆ [{8,0.625}, {4959,0.001807}, …… │
    │ 9   ┆ 1      ┆ [{9,0.674681}, {31,0.003125}, … │
    │ 9   ┆ 2      ┆ [{4606,0.001501}, {25,0.000115… │
    └─────┴────────┴─────────────────────────────────┘
    NOTE: 1st degree neighbors includes input fid. 
    This is useful when creating watchlists of whale fids.
    """
    start_time = time.perf_counter()
    results = []
    limit = max_neighbors
    degree = 1
    skip = 1 # 1st degree neighbors includes input fid.
    while limit > 0 and degree <= max_degree:
        df_start_time = time.perf_counter()
        scores = (
            graph.df.filter((pl.col("fid") == fid) & (pl.col("degree") == degree))
            .with_columns(pl.col("scores").list.slice(skip, limit + skip)) 
            .select(pl.col("scores"))
            .rows()
        )
        # When sample fid = 3, degree = 1 and limit = 2: 
        # [([{'i': 13683, 'v': 0.00046031096563011457}, 
        # {'i': 1941, 'v': 0.0011507774140752864}, 
        # {'i': 12504, 'v': 0.0005370294599018003}],)]
        logger.info(
            f"dataframe took {time.perf_counter() - df_start_time}"
            f" secs for k-{degree} for fid {fid}"
        )
        if len(scores) == 0:
            logger.info(f"fid {fid} has 0 k-{degree} neighbors")
            break
        if len(scores) > 0:
            results.extend(scores[0][0])
            # [{'i': 13683, 'v': 0.00046031096563011457}, 
            # {'i': 1941, 'v': 0.0011507774140752864}, 
            # {'i': 12504, 'v': 0.0005370294599018003}]
            logger.info(f"fid {fid} has {len(scores[0][0])} k-{degree} neighbors")
            limit = limit - len(results)
            degree = degree + 1
            skip = 0
    logger.info(
        f"{len(results)} results for fid {fid} took {time.perf_counter() - start_time} secs"
    )
    return results

import itertools
import random
import time
from typing import Annotated

import igraph
import numpy as np
import pandas
import requests
from fastapi import HTTPException, Query, Request
from loguru import logger

from ..config import settings
from ..models.graph_model import Graph, GraphType


# dependency to make it explicit that routers are accessing hidden state
# to avoid model name hardcoding in routers
# TODO clean up hardcoded names in function names; use enums
def get_following_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.following]


# def get_engagement_graph(request: Request) -> Graph:
#     return request.state.graphs[GraphType.engagement]


def get_ninetydays_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.ninetydays]


def find_vertex_idx(ig: igraph.GraphBase, fid: int) -> int:
    try:
        logger.debug(fid)
        return ig.vs.find(name=fid).index
    except:
        return None


async def go_eigentrust(
    pretrust: list[dict],
    # max_pt_id: np.int64,
    max_pt_id: int,
    localtrust: list[dict],
    # max_lt_id: np.int64,
    max_lt_id: int,
):
    start_time = time.perf_counter()

    req = {
        "pretrust": {
            "scheme": 'inline',
            # "size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
            "size": max_pt_id,
            "entries": pretrust,
        },
        "localTrust": {
            "scheme": 'inline',
            # "size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
            "size": max_lt_id,
            "entries": localtrust,
        },
        "alpha": settings.EIGENTRUST_ALPHA,
        # "epsilon": settings.EIGENTRUST_EPSILON,
        # "max_iterations": settings.EIGENTRUST_MAX_ITER,
        # "flatTail": settings.EIGENTRUST_FLAT_TAIL
    }

    logger.trace(req)
    response = requests.post(
        f"{settings.GO_EIGENTRUST_URL}/basic/v1/compute",
        json=req,
        headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
        timeout=settings.GO_EIGENTRUST_TIMEOUT_MS,
    )

    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise HTTPException(status_code=500, detail="Unknown error")
    trustscores = response.json()['entries']
    logger.info(
        f"eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores"
    )
    return trustscores


async def get_neighbors_scores(
    fids: list[int],
    graph: Graph,
    max_degree: int,
    max_neighbors: int,
) -> list[dict]:

    start_time = time.perf_counter()
    df = await _get_neighbors_edges(fids, graph, max_degree, max_neighbors)
    # Filter out entries where i == j
    df = df[df['i'] != df['j']]
    logger.info(
        f"dataframe took {time.perf_counter() - start_time} secs for {len(df)} edges"
    )

    if df.shape[0] < 1:
        raise HTTPException(status_code=404, detail="No neighbors")

    logger.trace(df)
    stacked = df.loc[:, ('i', 'j')].stack()
    logger.trace(stacked)
    pseudo_id, orig_id = stacked.factorize()
    logger.trace(pseudo_id)
    logger.trace(orig_id)

    # pseudo_df is a new dataframe to avoid modifying existing shared global df
    pseudo_df = pandas.Series(pseudo_id, index=stacked.index).unstack()
    pseudo_df.loc[:, ('v')] = df.loc[:, ('v')]

    fids_set = set(fids)
    if len(fids) > 1:
        # when more than 1 fid in input list, the neighbor edges may not have some input fids.
        pt_fids = orig_id.where(orig_id.isin(fids_set))
    else:
        pt_fids = fids_set
    pt_len = len(pt_fids)
    # pretrust = [{'i': fid, 'v': 1/pt_len} for fid in pt_fids]
    pretrust = [
        {'i': orig_id.get_loc(fid), 'v': 1 / pt_len}
        for fid in pt_fids
        if not np.isnan(fid)
    ]
    # max_pt_id = max(pt_fids)
    max_pt_id = len(orig_id)

    localtrust = pseudo_df.to_dict(orient="records")
    # max_lt_id = max(df['i'].max(), df['j'].max())
    max_lt_id = len(orig_id)

    logger.info(
        f"max_lt_id:{max_lt_id}, localtrust size:{len(localtrust)},"
        f" max_pt_id:{max_pt_id}, pretrust size:{len(pretrust)}"
    )

    i_scores = await go_eigentrust(
        pretrust=pretrust,
        max_pt_id=max_pt_id,
        localtrust=localtrust,
        max_lt_id=max_lt_id,
    )

    # rename i and v to fid and score respectively
    # also, filter out input fids
    fid_scores = [
        {'fid': int(orig_id[score['i']]), 'score': score['v']}
        for score in i_scores
        if score['i'] not in fids
    ]
    logger.debug(
        f"sample fid_scores:{random.sample(fid_scores, min(10, len(fid_scores)))}"
    )
    return fid_scores


async def get_neighbors_list(
    fids: list[int],
    graph: Graph,
    max_degree: Annotated[int, Query(le=5)] = 2,
    max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
) -> str:
    df = await _get_neighbors_edges(fids, graph, max_degree, max_neighbors)
    # WARNING we are operating on a shared dataframe...
    # ...inplace=False by default, explicitly setting here for emphasis
    out_df = (
        df.groupby(by='j')[['v']]
        .sum()
        .sort_values(by=['v'], ascending=False, inplace=False)
    )
    return out_df.index.to_list()


async def _get_neighbors_edges(
    fids: list[int],
    graph: Graph,
    max_degree: int,
    max_neighbors: int,
) -> pandas.DataFrame:

    start_time = time.perf_counter()
    neighbors_df = await _get_direct_edges_df(fids, graph, max_neighbors)
    logger.info(
        f"direct_edges_df took {time.perf_counter() - start_time} secs for {len(neighbors_df)} first degree edges"
    )
    k_neighbors_set = set(neighbors_df['j']) - set(fids)
    max_neighbors = max_neighbors - len(k_neighbors_set)
    if max_neighbors > 0 and max_degree > 1:

        start_time = time.perf_counter()
        k_set_next = await _fetch_korder_neighbors(
            fids, graph, max_degree, max_neighbors, min_degree=2
        )
        logger.info(
            f"{graph.type} took {time.perf_counter() - start_time} secs for {len(k_set_next)} neighbors"
        )

        start_time = time.perf_counter()
        k_neighbors_set.update(k_set_next)
        if settings.USE_PANDAS_PERF:
            # if multiple CPU cores are available
            k_df = graph.df.query('i in @k_neighbors_set').query(
                'j in @k_neighbors_set'
            )
        else:
            # filter with an '&' is slower because of the size of the dataframe
            # split the filtering so that indexes can be used if present
            # k_df = graph.df[graph.df['i'].isin(k_neighbors_set) & graph.df['j'].isin(k_neighbors_set)]
            k_df = graph.df[graph.df['i'].isin(k_neighbors_set)]
            k_df = k_df[k_df['j'].isin(k_neighbors_set)]
        # .loc will throw KeyError when fids have no outgoing actions
        ### in other words, some neighbor fids may not be present in 'i'
        # k_df = graph.df.loc[(k_neighbors_list, k_neighbors_list)]
        logger.info(
            f"k_df took {time.perf_counter() - start_time} secs for {len(k_df)} edges"
        )

        start_time = time.perf_counter()
        neighbors_df = pandas.concat([neighbors_df, k_df])
        logger.info(
            f"neighbors_df concat took {time.perf_counter() - start_time} secs for {len(neighbors_df)} edges"
        )

    return neighbors_df


async def _fetch_korder_neighbors(
    fids: list[int],
    graph: Graph,
    max_degree: int,
    max_neighbors: int,
    min_degree: int = 1,
) -> set[int]:

    # vids = [find_vertex_idx(graph.graph, fid) for fid in fids]
    # vids = list(filter(None, vids)) # WARNING - this filters vertex id 0 also
    vids = [
        vid
        for fid in fids
        for vid in [find_vertex_idx(graph.graph, fid)]
        if vid is not None
    ]
    if len(vids) <= 0:
        raise HTTPException(status_code=404, detail="Invalid fids")
    try:
        klists = []
        mindist_and_order = min_degree
        limit = max_neighbors
        while mindist_and_order <= max_degree:
            neighbors = graph.graph.neighborhood(
                vids, order=mindist_and_order, mode="out", mindist=mindist_and_order
            )
            # TODO prune the graph after sorting by edge weight
            klists.append(graph.graph.vs[neighbors[0][:limit]]["name"])
            limit = limit - len(neighbors[0])
            if limit <= 0:
                break  # we have reached limit of neighbors
            mindist_and_order += 1
        # end of while
        return set(itertools.chain(*klists))
    except ValueError:
        raise HTTPException(status_code=404, detail="Neighbors not found")


async def _get_direct_edges_df(
    fids: list[int],
    graph: Graph,
    max_neighbors: int,
) -> pandas.DataFrame:
    # WARNING we are operating on a shared dataframe...
    # ...inplace=False by default, explicitly setting here for emphasis
    out_df = graph.df[graph.df['i'].isin(fids)].sort_values(
        by=['v'], ascending=False, inplace=False
    )[:max_neighbors]
    return out_df


async def get_direct_edges_list(
    fids: list[int],
    graph: Graph,
    max_neighbors: int,
) -> pandas.DataFrame:
    start_time = time.perf_counter()
    out_df = await _get_direct_edges_df(fids, graph, max_neighbors)
    logger.info(
        f"dataframe took {time.perf_counter() - start_time} secs for {len(out_df)} direct edges"
    )
    return out_df[['j', 'v']].to_dict('records')

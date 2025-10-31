from typing import Annotated

from asyncpg.pool import Pool
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from ..dependencies import db_pool, db_utils, graph
from ..models.graph_model import Graph

router = APIRouter(tags=["Direct Links"])


@router.post("/engagement/handles")
async def get_direct_engagement_for_handles(
    handles: Annotated[
        list[str],
        Body(
            title="Handles",
            description="A list of handles.",
            examples=[["farcaster.eth", "varunsrin.eth", "farcaster", "v"]],
        ),
    ],
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_90_days_graph),
):
    """
    Given a list of input handles, return a list of handles
      that **only** the input handles have **directly engaged** with. \n
    Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
    """
    return await get_direct_following_for_handles(handles, limit, pool, graph_model)


@router.post("/following/handles")
async def get_direct_following_for_handles(
    handles: Annotated[
        list[str],
        Body(
            title="Handles",
            description="A list of handles.",
            examples=[["farcaster.eth", "varunsrin.eth", "farcaster", "v"]],
        ),
    ],
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_following_graph),
):
    """
    Given a list of input handles, return a list of handles
      that **only** the input handles are **directly** following. \n
    Example: ["farcaster.eth", "varunsrin.eth", "farcaster", "v"] \n
    """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    logger.debug(handles)
    res = await _get_direct_list_for_handles(handles, limit, pool, graph_model)
    logger.debug(f"Result has {len(res)} rows")
    return {"result": res}


async def _get_direct_list_for_handles(
    handles: list[str],
    limit: int,
    pool: Pool,
    graph_model: Graph,
) -> list[dict]:
    # fetch fid-address pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the fid-handle pairs
    fids = [int(hf["fid"]) for hf in handle_fids]

    return await _get_direct_list_for_fids(fids, limit, pool, graph_model)


@router.post("/engagement/fids")
async def get_direct_engagement_for_fids(
    fids: Annotated[
        list[int],
        Body(
            title="Farcaster IDs", description="A list of FIDs.", examples=[[1, 2, 3]]
        ),
    ],
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_90_days_graph),
):
    """
    Given a list of input fids, return a list of fids
      that **only** the input fids have **directly** engaged with. \n
    Example: [1, 2] \n
    """
    return await get_direct_following_for_fids(fids, limit, pool, graph_model)


@router.post("/following/fids")
async def get_direct_following_for_fids(
    fids: Annotated[
        list[int],
        Body(
            title="Farcaster IDs", description="A list of FIDs.", examples=[[1, 2, 3]]
        ),
    ],
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_following_graph),
):
    """
    Given a list of input fids, return a list of fids
      that **only** the input fids are **directly** following. \n
    Example: [1, 2] \n
    """
    if not (1 <= len(fids) <= 100):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    logger.debug(fids)
    res = await _get_direct_list_for_fids(fids, limit, pool, graph_model)
    logger.debug(f"Result has {len(res)} rows")
    return {"result": res}


async def _get_direct_list_for_fids(
    fids: list[int],
    limit: int,
    pool: Pool,
    graph_model: Graph,
) -> list[dict]:
    # get neighbors using fids
    neighbor_edges = await graph.get_direct_edges_list(fids, graph_model, limit)

    # convert the list of fid scores into a lookup with fid as key
    # [{fid1,score},{fid2,score}] -> {fid1:score, fid2:score}
    edge_score_map = {edge["j"]: edge["v"] for edge in neighbor_edges}

    edge_fids = list(edge_score_map.keys())

    # fetch address-handle pairs for neighbor addresses
    edge_fid_handles = await db_utils.get_unique_handle_metadata_for_fids(
        edge_fids, pool
    )

    # for every handle-fid pair, get the score from corresponding fid
    # {address, fname, username, fid} into {address, fname, username, fid, score}
    def fn_include_score(edge_fid_handle: dict) -> dict:
        score = edge_score_map[edge_fid_handle["fid"]]
        # trusted_fid_addr_handle is an 'asyncpg.Record'
        # 'asyncpg.Record' object does not support item assignment
        # need to create a new object with score
        return {
            "address": edge_fid_handle["address"],
            "fname": edge_fid_handle["fname"],
            "username": edge_fid_handle["username"],
            "fid": edge_fid_handle["fid"],
            "score": score,
        }

    # end of def fn_trust_score_with_handle_fid

    results = list(map(fn_include_score, edge_fid_handles))

    # sort by score
    results = sorted(results, key=lambda d: d["score"], reverse=True)

    return results

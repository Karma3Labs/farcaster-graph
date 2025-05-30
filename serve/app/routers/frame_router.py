from typing import Annotated

from asyncpg.pool import Pool
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from ..dependencies import db_pool, db_utils, graph
from ..models.graph_model import Graph
from ..models.score_model import ScoreAgg, Voting, Weights

router = APIRouter(tags=["Frames"])


@router.get("/global/rankings")
async def get_top_frames(
    # TODO consider using path parameter for better observality
    agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = 'L1C10R5',
    details: Annotated[bool | None, Query()] = False,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    recent: Annotated[bool | None, Query()] = True,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get a list of frame urls that are used by highly ranked profiles. \n
    This API takes five optional parameters -
      agg, weights, details, offset and limit. \n
    Parameter 'agg' is used to define the aggregation function and
      can take any of the following values - `rms`, `sumsquare`, `sum`. \n
    Parameter 'weights' is used to define the weights to be assigned
      to like, cast and recast actions by profiles. \n
    Parameter 'details' is used to specify whether
      the original cast list should be returned for each frame in the ranking. \n
    Parameter 'recent' is used to specify whether or not
      the age of the cast interaction should be considered.\n
    (Note: cast hashes and warpcast urls are returned in chronological order ie., **oldest first**)
    (*NOTE*: `details=True` will result in a few extra hundred milliseconds in response times).\n
    (**NOTE**: the API returns upto a max of 100 cast hashes and 100 warpcast urls when details=True).\n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    By default, agg=rms, weights='L1C10R5', details=False, offset=0, limit=100 and recent=True
      i.e., returns recent top 100 frame urls.
    """
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    if details:
        frames = await db_utils.get_top_frames_with_cast_details(
            agg,
            weights,
            offset=offset,
            limit=limit,
            recent=recent,
            decay=False,  # True results in high latency
            pool=pool,
        )
    else:
        frames = await db_utils.get_top_frames(
            agg,
            weights,
            offset=offset,
            limit=limit,
            recent=recent,
            decay=False,  # True results in high latency
            pool=pool,
        )
    return {"result": frames}


@router.post("/personalized/rankings/fids")
async def get_personalized_frames_for_fids(
    fids: Annotated[
        list[int],
        Body(
            title="Farcaster IDs", description="A list of FIDs.", examples=[[1, 2, 3]]
        ),
    ],
    # TODO consider using path parameter for better observality
    agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = 'L1C10R5',
    voting: Annotated[Voting | None, Query()] = Voting.SINGLE,
    k: Annotated[int, Query(le=5)] = 2,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    recent: Annotated[bool | None, Query()] = True,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_ninetydays_graph),
):
    """
    Given a list of input fids, return a list of frame urls
      used by the extended trust network of the input fids. \n
    This API takes four optional parameters - agg, weights, k and limit. \n
    Parameter 'agg' is used to define the aggregation function and
      can take any of the following values - `rms`, `sumsquare`, `sum` \n
    Parameter 'weights' is used to define the weights to be assigned
      to like, cast and recast actions by profiles. \n
    Parameter 'voting' is used to decide whether there is a single vote per neighbor
      or multiple votes per neigbor when deriving the frames score. \n
    Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
    By default, agg=rms, weights='L1C10R5', voting='single', k=2 and limit=100.
    """
    if not (1 <= len(fids) <= 100):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    logger.debug(fids)

    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    # compute eigentrust on the neighbor graph using fids
    trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

    frames = await db_utils.get_neighbors_frames(
        agg,
        weights,
        voting,
        trust_scores=trust_scores,
        limit=limit,
        recent=recent,
        pool=pool,
    )
    return {"result": frames}


@router.post("/personalized/rankings/handles")
async def get_personalized_frames_for_handles(
    handles: Annotated[
        list[str],
        Body(
            title="Handles",
            description="A list of handles.",
            examples=[["farcaster.eth", "varunsrin.eth", "farcaster", "v"]],
        ),
    ],
    # TODO consider using path parameter for better observality
    agg: Annotated[ScoreAgg | None, Query()] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = 'L1C10R5',
    voting: Annotated[Voting | None, Query()] = Voting.SINGLE,
    k: Annotated[int, Query(le=5)] = 2,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    recent: Annotated[bool | None, Query()] = True,
    pool: Pool = Depends(db_pool.get_db),
    graph_model: Graph = Depends(graph.get_ninetydays_graph),
):
    """
    Given a list of input handles, return a list of frame urls
      used by the extended trust network of the input handles. \n
    This API takes four optional parameters - agg, weights, k and limit. \n
    Parameter 'agg' is used to define the aggregation function and
      can take any of the following values - `rms`, `sumsquare`, `sum` \n
    Parameter 'weights' is used to define the weights to be assigned
      to like, cast and recast actions by profiles. \n
    Parameter 'voting' is used to decide whether there is a single vote per neighbor
      or multiple votes per neigbor when deriving the frames score. \n
    Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
    By default, agg=rms, weights='L1C10R5', voting='single', k=2 and limit=100.
    """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    logger.debug(handles)

    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    # fetch handle-address pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the fid-handle pairs
    fids = [int(hf["fid"]) for hf in handle_fids]

    # compute eigentrust on the neighbor graph using fids
    trust_scores = await graph.get_neighbors_scores(fids, graph_model, k, limit)

    frames = await db_utils.get_neighbors_frames(
        agg,
        weights,
        voting,
        trust_scores=trust_scores,
        limit=limit,
        recent=recent,
        pool=pool,
    )
    return {"result": frames}

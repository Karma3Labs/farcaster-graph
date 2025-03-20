from typing import Annotated, List
import urllib.parse
import asyncio

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool
from pydantic_core import ValidationError

from ..models.graph_model import Graph, GraphTimeframe
from ..models.score_model import ScoreAgg, Weights
from ..models.feed_model import FeedMetadata
from ..models.channel_model import ChannelRankingsTimeframe
from ..dependencies import graph, db_pool, db_utils
from ..config import settings
from . import channel_router

router = APIRouter(tags=["Casts"])


@router.get("/personalized/popular/{fid}", tags=["For You Feed", "Neynar For You Feed"])
async def get_popular_casts_for_fid(
    fid: int,
    agg: Annotated[
        ScoreAgg | None,
        Query(
            description="Define the aggregation function - `rms`, `sumsquare`, `sum`"
        ),
    ] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = "L1C10R5Y1",
    k: Annotated[int, Query(le=5)] = 1,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=50)] = 25,
    graph_limit: Annotated[int | None, Query(le=1000)] = 100,
    lite: Annotated[bool, Query()] = True,
    timeframe: GraphTimeframe = Query(GraphTimeframe.lifetime),
    provider_metadata: Annotated[str | None, Query()] = None,
    pool: Pool = Depends(db_pool.get_db),
    lifetime_model: Graph = Depends(graph.get_engagement_graph),
    ninetyday_model: Graph = Depends(graph.get_ninetydays_graph),
):
    """
      Get a list of casts that have been interacted with the most
      in a user's extended network. \n
    This API takes optional parameters -
      agg, weights, k, offset, limit  and lite. \n
    Parameter 'agg' is used to define the aggregation function and
      can take any of the following values - `rms`, `sumsquare`, `sum`. \n
    Parameter `weights` is used to define the weights to be assigned
      to (L)ikes, (C)asts, (R)ecasts and repl(Y) actions by profiles. \n
    Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
    Parameter 'lite' is used to constrain the result to just cast hashes. \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    Parameter 'graph_limit' is used to constrain the graph neighborhood. \n
    By default, agg=sumsquare, weights='L1C10R5Y1', k=1, offset=0,
      limit=25, graph_limit=100 and lite=true
      i.e., returns recent 25 popular casts.
    """
    if provider_metadata:
        logger.info(f"Ignoring parameters and using metadata {provider_metadata}")
        # Example: %7B%22feedType%22%3A%22popular%22%2C%22timeframe%22%3A%22month%22%7D
        md_str = urllib.parse.unquote(provider_metadata)
        logger.info(f"Provider metadata: {md_str}")
        try:
            metadata = FeedMetadata.validate_json(md_str)
        except ValidationError as e:
            logger.error(f"Error while validating provider metadata: {e}")
            logger.error(f"errors(): {e.errors()}")
            raise HTTPException(status_code=400, detail=f"Error while validating provider metadata: {e.errors()}")

        channel_ids = await db_utils.get_channel_ids_for_fid(
            fid=fid, limit=settings.MAX_CHANNELS_PER_USER, pool=pool
        )
        logger.info(f"channel_ids: {channel_ids}")
        channel_tasks = []
        for channel_id in channel_ids:
            channel_tasks.append(
                channel_router.get_popular_channel_casts(
                    channel=channel_id['channel_id'],
                    rank_timeframe=ChannelRankingsTimeframe.SIXTY_DAYS,
                    offset=0,
                    limit=25,
                    lite=True,
                    provider_metadata=provider_metadata,
                    pool=pool
                )
            )
        result_list = await asyncio.wait_for(asyncio.gather(*channel_tasks, return_exceptions=True), timeout=5)
        casts = []
        for result in result_list:
            if not isinstance(result, Exception):
                casts.extend(result['result'])
        sorted_casts = sorted(casts, key=lambda d: d['age_hours'])
        return {"result": sorted_casts}
    else:
        try:
            weights = Weights.from_str(weights)
        except:
            raise HTTPException(
                status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
            )

        # compute eigentrust on the neighbor graph using fids
        trust_scores = await graph.get_neighbors_scores(
            [fid],
            ninetyday_model if timeframe == GraphTimeframe.ninetydays else lifetime_model,
            k,
            graph_limit,
        )

        # trust_scores = sorted(trust_scores, key=lambda d: d['score'], reverse=True)
        casts = await db_utils.get_popular_neighbors_casts(
            agg,
            weights,
            trust_scores=trust_scores,
            offset=offset,
            limit=limit,
            lite=lite,
            pool=pool,
        )
        return {"result": casts}


@router.get("/personalized/recent/{fid}")
async def get_personalized_casts_for_fid(
    fid: int,
    k: Annotated[int, Query(le=5)] = 1,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=50)] = 25,
    graph_limit: Annotated[int | None, Query(le=1000)] = 100,
    lite: Annotated[bool, Query()] = True,
    timeframe: GraphTimeframe = Query(GraphTimeframe.lifetime),
    pool: Pool = Depends(db_pool.get_db),
    lifetime_model: Graph = Depends(graph.get_engagement_graph),
    ninetyday_model: Graph = Depends(graph.get_ninetydays_graph),
):
    """
      Get a list of casts that have been casted by the
        popular profiles in a user's extended network. \n
    This API takes optional parameters -
      k, offset, limit, graph_limit and lite. \n
    Parameter 'k' is used to constrain the social graph to k-degrees of separation. \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    Parameter 'graph_limit' is used to constrain the graph neighborhood. \n
    Parameter 'lite' is used to constrain the result to just cast hashes. \n
    By default, k=1, offset=0, limit=25, graph_limit=100 and lite=true
      i.e., returns recent 25 frame urls casted by extended network.
    """
    # compute eigentrust on the neighbor graph using fids
    trust_scores = await graph.get_neighbors_scores(
        [fid],
        ninetyday_model if timeframe == GraphTimeframe.ninetydays else lifetime_model,
        k,
        graph_limit,
    )

    casts = await db_utils.get_recent_neighbors_casts(
        trust_scores=trust_scores, offset=offset, limit=limit, lite=lite, pool=pool
    )
    if not lite:
        casts = sorted(casts, key=lambda d: d["cast_score"], reverse=True)
    return {"result": casts}


@router.post("/curated/recent/")
async def get_curated_casts_for_fid(
    fids: List[int],
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=50)] = 25,
    pool: Pool = Depends(db_pool.get_db),
):
    """
      Get a list of casts that have been casted by the
        an list of FIDs. \n
    This API takes optional parameters -
      offset, limit \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    Limit Parameter is set to 25 as default and a max of 50
    By default, offset=0, limit=25
      i.e., returns recent 25 frame urls cast by extended network.
    """
    if not (1 <= len(fids) <= 150):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 150 entries"
        )
    logger.debug(fids)

    casts = await db_utils.get_recent_casts_by_fids(
        fids=fids, offset=offset, limit=limit, pool=pool
    )

    return {"result": casts}


@router.get("/global/trending")
async def get_trending_casts(
    agg: Annotated[
        ScoreAgg | None,
        Query(
            description="Define the aggregation function - `rms`, `sumsquare`, `sum`"
        ),
    ] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = "L1C10R5Y1",
    score_mask: Annotated[int | None, Query(ge=0, le=10)] = 5,
    offset: Annotated[int | None, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=0, le=5000)] = 100,
    lite: Annotated[bool, Query()] = True,
    pool: Pool = Depends(db_pool.get_db),
):
    """
      Get a list of casts that have been cast by the
        popular profiles in a user's extended network. \n
    This API takes optional parameters -
      agg, weights, offset, limit and lite. \n
    Parameter 'agg' is used to define the aggregation function and
      can take any of the following values - `rms`, `sumsquare`, `sum`. \n
    Parameter 'weights' is used to define the weights to be assigned
      to (L)ikes, (C)asts, (R)ecasts and repl(Y) actions by profiles. \n
    Parameter 'score_mask' is used to define how many decimal places to consider
      when deciding whether or not to show a cast.
      The lower this number the higher the score that a cast needs to have
      to be included in the feed. \n
    Parameter 'lite' is used to constrain the result to just cast hashes. \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    By default, agg=sumsquare, weights='L1C10R5Y1', score_mask=6, offset=0,
      limit=25, and lite=true
      i.e., returns recent 100 popular casts whose score is greater than 1e-6.
    """
    # compute eigentrust on the neighbor graph using fids
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    if lite:
        casts = await db_utils.get_trending_casts_lite(
            agg=agg,
            weights=weights,
            score_threshold_multiplier=pow(10, score_mask),
            offset=offset,
            limit=limit,
            pool=pool,
        )
    else:
        casts = await db_utils.get_trending_casts_heavy(
            agg=agg,
            weights=weights,
            score_threshold_multiplier=pow(10, score_mask),
            offset=offset,
            limit=limit,
            pool=pool,
        )
    return {"result": casts}

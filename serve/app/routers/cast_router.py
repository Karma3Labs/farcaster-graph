import asyncio
import urllib.parse
from asyncio import TimeoutError
from typing import Annotated, List

import niquests
from asyncpg.pool import Pool
from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from pydantic_core import ValidationError

from . import channel_router
from ..config import settings
from ..dependencies import graph, db_pool, db_utils
from ..models.channel_model import ChannelRankingsTimeframe
from ..models.feed_model import FeedMetadata
from ..models.graph_model import Graph, GraphTimeframe
from ..models.score_model import ScoreAgg, Weights

router = APIRouter(tags=["Casts"])


async def get_user_pinned_channels(fid: int) -> list[str]:
    endpoint = f"{settings.CURA_API_ENDPOINT}/internal/user-pinned-channels"
    logger.info(f"Getting pinned channels for fid {fid}")
    resp = await niquests.apost(
        endpoint,
        headers={"Authorization": f"Bearer {settings.CURA_API_KEY}"},
        json={"fid": fid},
    )
    resp.raise_for_status()
    try:
        return resp.json()["data"]
    except KeyError:
        return []


async def task_with_timeout(task_id, task_coroutine, task_timeout):
    try:
        result = await asyncio.wait_for(task_coroutine, timeout=task_timeout)
        return (task_id, result)
    except TimeoutError:
        return (task_id, None)


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
    timeframe: GraphTimeframe = Query(GraphTimeframe.ninetydays),
    provider_metadata: Annotated[str | None, Query()] = None,
    pool: Pool = Depends(db_pool.get_db),
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
            raise HTTPException(
                status_code=400,
                detail=f"Error while validating provider metadata: {e.errors()}",
            )

        if metadata.channels is not None:
            # TODO(ek): validate channel IDs?
            channel_ids = set(metadata.channels)
        else:
            rows = await db_utils.get_channel_ids_for_fid(
                fid=fid, limit=settings.MAX_CHANNELS_PER_USER, pool=pool
            )
            channel_ids = {row["channel_id"] for row in rows}
        pinned_channels = set(await get_user_pinned_channels(fid))
        logger.info(f"Pinned channel_ids for fid {fid}: {pinned_channels}")
        channel_ids |= pinned_channels
        logger.info(f"channel_ids for fid {fid}: {channel_ids}")
        if len(channel_ids) == 0:
            logger.info(f"No channels found for fid: {fid}")
            return {"result": []}

        channel_tasks = []

        for channel_id in channel_ids:
            channel_tasks.append(
                task_with_timeout(
                    task_id=channel_id,
                    task_coroutine=channel_router.get_popular_channel_casts(
                        channel=channel_id,
                        rank_timeframe=ChannelRankingsTimeframe.SIXTY_DAYS,
                        offset=offset,
                        limit=limit,
                        lite=True,
                        provider_metadata=provider_metadata,
                        pool=pool,
                    ),
                    task_timeout=metadata.timeout_secs,
                )
            )
        result_list = await asyncio.gather(*channel_tasks, return_exceptions=True)

        timedout_channel_ids = []
        error_channel_ids = []
        success_channel_ids = []
        casts = []
        for task_id, result in result_list:
            extra = {"channel_id": task_id}
            if result is None:
                timedout_channel_ids.append(task_id)
            elif isinstance(result, Exception):
                error_channel_ids.append(task_id)
            else:
                success_channel_ids.append(task_id)
                casts.extend(dict(cast) | extra for cast in result["result"])
        if len(timedout_channel_ids) > 0:
            logger.error(f"timedout_channel_ids: {timedout_channel_ids}")
        if len(error_channel_ids) > 0:
            logger.error(f"error_channel_ids: {error_channel_ids}")
        if len(success_channel_ids) == 0:
            raise HTTPException(
                status_code=500, detail="Errors and or timeoutswhile fetching casts"
            )

        def cast_key(d):
            return (0 if d["channel_id"] in pinned_channels else 1, d["age_hours"])

        sorted_casts = sorted(casts, key=cast_key)
        for cast in sorted_casts:
            del cast['channel_id']
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
            ninetyday_model,
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
    timeframe: GraphTimeframe = Query(GraphTimeframe.ninetydays),
    pool: Pool = Depends(db_pool.get_db),
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
        ninetyday_model,
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

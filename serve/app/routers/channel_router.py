from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from loguru import logger
from asyncpg.pool import Pool
from ..models.score_model import ScoreAgg, Weights, Sorting_Order
from ..models.channel_model import ChannelRankingsTimeframe, CHANNEL_RANKING_STRATEGY_NAMES
from ..dependencies import db_pool, db_utils
from ..utils import fetch_channel

router = APIRouter(tags=["Channel OpenRank Scores"])


@router.get("/rankings/{channel}")
async def get_top_channel_profiles(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        lite: bool = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids based on the engagement relationships in the given channel
    and scored by Eigentrust algorithm. \n
  Specify one of the following as channel_id:
    `degen`, `base`, `optimism`, `founders`, `farcaster`, `op-stack`, `new-york`
  This API takes two optional parameters - offset and limit. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return. \n
  Parameter 'lite' is used to indicate if additional details like
    fnames and percentile should be returned or not. \n
  By default, limit is 100, offset is 0 and lite is True i.e., returns top 100 fids.
  """
    ranks = await db_utils.get_top_channel_profiles(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        offset=offset,
        limit=limit,
        lite=lite,
        pool=pool)
    return {"result": ranks}


@router.post("/rankings/{channel}/fids")
async def get_channel_rank_for_fids(
        # Example: -d '[1, 2]'
        channel: str,
        fids: list[int],
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        lite: bool = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input fids, return a list of fids
    that are ranked based on the engagement relationships in the channel
    and scored by Eigentrust algorithm. \n
    Example: [1, 2] \n
  Parameter 'lite' is used to indicate if additional details like
    fnames and percentile should be returned or not. \n
  By default, lite is True
  """
    if not (1 <= len(fids) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    ranks = await db_utils.get_channel_profile_ranks(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        fids=fids,
        lite=lite,
        pool=pool)
    return {"result": ranks}


@router.post("/rankings/{channel}/handles")
async def get_channel_rank_for_handles(
        # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
        channel: str,
        handles: list[str],
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input handles, return a list of handles
    that are ranked based on the engagement relationships in the channel
    and scored by Eigentrust algorithm. \n
    Example: ["dwr.eth", "varunsrin.eth"] \n
  """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    # fetch handle-fid pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the handle-fid pairs
    fids = [hf["fid"] for hf in handle_fids]

    ranks = await db_utils.get_channel_profile_ranks(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        fids=fids,
        lite=False,
        pool=pool)
    return {"result": ranks}


@router.get("/casts/popular/{channel}")
async def get_popular_channel_casts(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        agg: Annotated[ScoreAgg | None,
                       Query(description="Define the aggregation function" \
                                         " - `rms`, `sumsquare`, `sum`")] = ScoreAgg.SUMSQUARE,
        weights: Annotated[str | None, Query()] = 'L1C10R5Y1',
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=50)] = 25,
        lite: Annotated[bool, Query()] = True,
        sorting_order: Annotated[Sorting_Order, Query()] = Sorting_Order.POPULAR,
        pool: Pool = Depends(db_pool.get_db),
):
    """
  Get a list of recent casts that are the most popular
    based on Eigentrust scores of fids in the channel. \n
  This API takes optional parameters -
    agg, weights, offset, limit andlite. \n
  Parameter 'agg' is used to define the aggregation function and
    can take any of the following values - `rms`, `sumsquare`, `sum`. \n
  Parameter 'weights' is used to define the weights to be assigned
    to (L)ikes, (C)asts, (R)ecasts and repl(Y) actions by profiles. \n
  Parameter 'lite' is used to constrain the result to just cast hashes. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return. \n
  By default, agg=sumsquare, weights='L1C10R5Y1', offset=0,
    limit=25, and lite=true
    i.e., returns recent 25 popular casts.
  """
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

    if lite:
        casts = await db_utils.get_popular_channel_casts_lite(
            channel_id=channel,
            channel_url=fetch_channel(channel_id=channel),
            strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
            agg=agg,
            weights=weights,
            offset=offset,
            limit=limit,
            sorting_order=sorting_order,
            pool=pool)
    else:
        casts = await db_utils.get_popular_channel_casts_heavy(
            channel_id=channel,
            channel_url=fetch_channel(channel_id=channel),
            strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
            agg=agg,
            weights=weights,
            offset=offset,
            limit=limit,
            sorting_order=sorting_order,
            pool=pool)
    print(sorting_order)
    return {"result": casts}


@router.get("/experiments/degen/casts")
async def get_popular_casts_from_degen_graph(
        agg: Annotated[ScoreAgg | None,
                       Query(description="Define the aggregation function" \
                                         " - `rms`, `sumsquare`, `sum`")] = ScoreAgg.SUMSQUARE,
        weights: Annotated[str | None, Query()] = 'L1C10R5Y1',
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=10000)] = 100,
        sorting_order: Annotated[Sorting_Order, Query()] = Sorting_Order.POPULAR,
        pool: Pool = Depends(db_pool.get_db),
):
    """
  Get a list of recent casts that are the most popular
    based on Eigentrust scores of fids in the channel. \n
  This API takes optional parameters -
    agg, weights, offset, limit andlite. \n
  Parameter 'agg' is used to define the aggregation function and
    can take any of the following values - `rms`, `sumsquare`, `sum`. \n
  Parameter 'weights' is used to define the weights to be assigned
    to (L)ikes, (C)asts, (R)ecasts and repl(Y) actions by profiles. \n
  Parameter 'lite' is used to constrain the result to just cast hashes. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return. \n
  By default, agg=sumsquare, weights='L1C10R5Y1', offset=0,
    limit=25, and lite=true
    i.e., returns recent 25 popular casts.
  """
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")

    casts = await db_utils.get_popular_degen_casts(
        agg=agg,
        weights=weights,
        offset=offset,
        limit=limit,
        sorting_order=sorting_order,
        pool=pool)

    return {"result": casts}


@router.get("/followers/{channel}")
async def get_top_channel_followers(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=500000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids who are followers of the channel
  and their latest global rank channel rank and name
  This API takes two optional parameters - offset and limit. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return.
  By default, limit is 100, offset is 0 and lite is True i.e., returns top 100 fids.
  """
    followers = await db_utils.get_top_channel_followers(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        offset=offset,
        limit=limit,
        pool=pool)
    return {"result": followers}


@router.get("/repliers/{channel}")
async def get_top_channel_repliers(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=500000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids who are followers of the channel
  and their latest global rank channel rank and name
  This API takes two optional parameters - offset and limit. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return.
  By default, limit is 100, offset is 0 and lite is True i.e., returns top 100 fids.
  """
    followers = await db_utils.get_top_channel_repliers(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        offset=offset,
        limit=limit,
        pool=pool)
    return {"result": followers}


@router.get("/top-casts/{channel_id}")
async def get_trending_casts(
        channel: str,
        channel_strategy: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.LIFETIME),
        agg: Annotated[ScoreAgg | None,
                       Query(description="Define the aggregation function" \
                                         "`sumsquare`")] = ScoreAgg.SUMSQUARE,
        offset: Annotated[int | None, Query(ge=0)] = 0,
        limit: Annotated[int | None, Query(ge=0, le=5000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
    casts = await db_utils.get_trending_channel_casts(
        channel_id=channel,
        channel_url=fetch_channel(channel_id=channel),
        channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[channel_strategy],
        agg=agg,
        offset=offset,
        limit=limit,
        pool=pool
    )

    return {"result": casts}

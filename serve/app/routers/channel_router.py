from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from loguru import logger
from asyncpg.pool import Pool
from ..models.score_model import ScoreAgg, Weights, Sorting_Order
from ..models.channel_model import (
  ChannelRankingsTimeframe, CHANNEL_RANKING_STRATEGY_NAMES, OpenrankCategory,
  ChannelPointsOrderBy, ChannelEarningsOrderBy, ChannelEarningsType,
  ChannelEarningsScope
)
from ..dependencies import db_pool, db_utils
from .. import utils
from ..utils import fetch_channel

router = APIRouter(tags=["Channel OpenRank Scores"])

@router.get("/openrank/{channel}")
async def get_top_openrank_channel_profiles(
  channel: str,
  category: OpenrankCategory = Query(OpenrankCategory.PROD),
  offset: Annotated[int | None, Query()] = 0,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  pool: Pool = Depends(db_pool.get_db)
):
  ranks = await db_utils.get_top_openrank_channel_profiles(
        channel_id=channel,
        category=category.value,
        offset=offset,
        limit=limit,
        pool=pool)
  return {"result": ranks}

@router.get("/points/{channel}")
async def get_top_channel_balances(
        channel: str,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        lite: bool = True,
        orderby: ChannelPointsOrderBy = Query(ChannelPointsOrderBy.TOTAL_POINTS),
        pool: Pool = Depends(db_pool.get_db)
):
  balances = await db_utils.get_top_channel_balances(
        channel_id=channel,
        offset=offset,
        limit=limit,
        lite=lite,
        orderby=orderby,
        pool=pool)
  return {"result": balances}

@router.get("/tokens/{channel}")
async def get_top_token_balances(
        channel: str,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        lite: bool = True,
        orderby: ChannelEarningsOrderBy = Query(ChannelEarningsOrderBy.TOTAL),
        pool: Pool = Depends(db_pool.get_db)
):
  balances = await db_utils.get_top_channel_earnings(
        channel_id=channel,
        offset=offset,
        limit=limit,
        lite=lite,
        earnings_type=ChannelEarningsType.TOKENS,
        orderby=orderby,
        pool=pool)
  return {"result": balances}

@router.get("/tokens/{channel}/claim")
async def get_token_claim(
        channel: str,
        fid: int,
        pool: Pool = Depends(db_pool.get_db)
):
    # check local pg database first before calling smart contract manager
    balance = await db_utils.get_fid_channel_token_balance(
        channel_id=channel, fid=fid, pool=pool
    )
    if not balance:
        logger.error(f"No entry in token balance table for {channel} {fid}")
        raise HTTPException(status_code=404, detail="No tokens to claim.")
    channel_token = await utils.fetch_channel_token(channel_id=channel)
    if not channel_token:
        logger.error(
            f"Weird! Balance for {channel} {fid} exists."
            f" But, no tokens deployed."
            f" Channel {channel} is probably used for testing."
        )
        raise HTTPException(status_code=404, detail="No tokens to claim.")
        # logger.warning("using hardcoded token details until we deploy smart contract manager")
        # channel_token = {
        #     "id": "3487e020-2090-4d4a-a316-37824093f1a1",
        #     "channelId": "openrank",
        #     "walletAddress": "0xD5Fda8AeA42347D9ab4dEA6eF06D283B24CdD5FB",
        #     "tokenAddress": "0x31353b81D4C66953A232e080E1c792e7f7B4fc9F",
        #     "claimContractAddress": "0xd12b4c4550fab025fae9f503309b986bdcd95416",
        #     "deployTokenTx": "0x9e80a4064bfa80e1350bc79667e5cdeb28585b72db16b122ed47bea0df440457",
        #     "deployContractTx": "0x4d2f907bcef9e8111ad0463bfda2ac171bf3c84133331429c18d4b20d1c0aa71",
        #     "createdAt": "2024-12-18T19:00:05.533472+00:00",
        #     "tokenMetadata": {
        #       "name": "test openrank",
        #       "supply": "1000000000000000000000000000",
        #       "symbol": "TOR",
        #       "chainId": "84532",
        #       "imageHash": None,
        #       "creatorCut": "500",
        #       "initialTick": "-207400",
        #       "feeBasisPoints": "10000"
        #     }
        # }
    return {"result": {**balance, **channel_token}}

@router.get("/distribution/preview/{channel}")
async def get_tokens_distrib_preview(
        channel: str,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        scope: ChannelEarningsScope = Query(ChannelEarningsScope.AIRDROP),
        type: ChannelEarningsType = Query(ChannelEarningsType.TOKENS),
        pool: Pool = Depends(db_pool.get_db)
):
  if type == ChannelEarningsType.TOKENS:
    distributions = await db_utils.get_tokens_distrib_preview(
          channel_id=channel,
          offset=offset,
          limit=limit,
          scope=scope,
          pool=pool)
  elif type == ChannelEarningsType.POINTS:
    if scope == ChannelEarningsScope.AIRDROP:
        raise HTTPException(status_code=400, detail="Points distribution preview not available for airdrop")
    distributions = await db_utils.get_points_distrib_preview(
          channel_id=channel,
          offset=offset,
          limit=limit,
          pool=pool)
  return {"result": distributions}

@router.get("/distribution/overview/{channel}")
async def get_tokens_distrib_overview(
        channel: str,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
  distribribution_stats = await db_utils.get_tokens_distrib_overview(
        channel_id=channel,
        offset=offset,
        limit=limit,
        pool=pool)
  return {"result": distribribution_stats}

@router.get("/distribution/details/{channel}")
async def get_tokens_distrib_details(
        channel: str,
        dist_id: Annotated[int | None, Query()] = None,
        batch_id: Annotated[int | None, Query()] = 1,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
  details = await db_utils.get_tokens_distrib_details(
        channel_id=channel,
        dist_id=dist_id,
        batch_id=batch_id,
        offset=offset,
        limit=limit,
        pool=pool)
  return {"result": details}

@router.get("/rankings/{channel}")
async def get_top_channel_profiles(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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

@router.get("/rankings/{channel}/stats")
async def get_channel_stats(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get basic statistics about the rankings in a channel. \n
  Specify one of the following as channel_id:
    `degen`, `base`, `optimism`, `founders`, `farcaster`, `op-stack`, `new-york`
  """
    stats = await db_utils.get_channel_stats(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        pool=pool)
    return {"result": stats}

@router.post("/rankings/{channel}/fids")
async def get_channel_rank_for_fids(
        # Example: -d '[1, 2]'
        channel: str,
        fids: list[int],
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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


@router.get("/casts/daily/{channel}")
async def get_trending_casts(
        channel: str,
        channel_strategy: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
        max_cast_age: Annotated[int | None, Query(ge=0, le=30)] = 1,
        agg: Annotated[ScoreAgg | None,
                       Query(description="Define the aggregation function" \
                                         " - `rms`, `sumsquare`, `sum`")] = ScoreAgg.SUM,
        weights: Annotated[str | None, Query()] = 'L1C0R1Y1',
        time_decay: Annotated[bool, Query()] = True,
        normalize: Annotated[bool, Query()] = True,
        offset: Annotated[int | None, Query(ge=0)] = 0,
        limit: Annotated[int | None, Query(ge=0, le=5000)] = 100,
        sorting_order: Annotated[Sorting_Order, Query()] = Sorting_Order.POPULAR,
        pool: Pool = Depends(db_pool.get_db)
):
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(status_code=400, detail="Weights should be of the form 'LxxCxxRxx'")
    casts = await db_utils.get_trending_channel_casts(
        channel_id=channel,
        channel_url=fetch_channel(channel_id=channel),
        channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[channel_strategy],
        max_cast_age=max_cast_age,
        agg=agg,
        weights=weights,
        time_decay=time_decay,
        normalize=normalize,
        offset=offset,
        limit=limit,
        sorting_order=sorting_order,
        pool=pool
    )

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
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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

@router.get("/holders/{channel}")
async def get_top_channel_holders(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
        orderby: ChannelEarningsOrderBy = Query(ChannelEarningsOrderBy.TOTAL),
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=500000)] = 100,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids who hold points or tokens
  and their latest global rank channel rank and name
  This API takes three optional parameters - offset and limit. \n
  Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
  Parameter 'limit' is used to specify the number of results to return.
  By default, limit is 100, offset is 0 and lite is True i.e., returns top 100 fids.
  """
    followers = await db_utils.get_top_channel_holders(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        orderby=orderby,
        offset=offset,
        limit=limit,
        pool=pool)
    return {"result": followers}


@router.get("/repliers/{channel}")
async def get_top_channel_repliers(
        channel: str,
        rank_timeframe: ChannelRankingsTimeframe = Query(ChannelRankingsTimeframe.SIXTY_DAYS),
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


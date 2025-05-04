import json
import urllib.parse
from itertools import batched
from typing import Annotated

from asyncpg.pool import Pool
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic_core import ValidationError

from .. import utils
from ..config import DBVersion, settings
from ..dependencies import db_pool, db_utils
from ..models.channel_model import (
    CHANNEL_RANKING_STRATEGY_NAMES,
    ChannelEarningsOrderBy,
    ChannelEarningsScope,
    ChannelEarningsType,
    ChannelFidType,
    ChannelPointsOrderBy,
    ChannelRankingsTimeframe,
    OpenrankCategory,
)
from ..models.feed_model import (
    CASTS_AGE,
    PARENT_CASTS_AGE,
    CastsTimeDecay,
    ChannelTimeframe,
    FarconFeed,
    FeedMetadata,
    PopularFeed,
    ScoresMetadata,
    SearchScores,
    SortingOrder,
    TrendingFeed,
)
from ..models.score_model import ScoreAgg, Weights
from ..utils import fetch_channel

router = APIRouter()


@router.get("/openrank/{channel}", tags=["Experimental"])
async def get_top_openrank_channel_profiles(
    channel: str,
    category: OpenrankCategory = Query(OpenrankCategory.PROD),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
):
    ranks = await db_utils.get_top_openrank_channel_profiles(
        channel_id=channel,
        category=category.value,
        offset=offset,
        limit=limit,
        pool=pool,
    )
    return {"result": ranks}


@router.get("/points/{channel}", tags=["Deprecated"])
async def get_top_channel_balances(
    channel: str,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    lite: bool = True,
    orderby: ChannelPointsOrderBy = Query(ChannelPointsOrderBy.TOTAL_POINTS),
    pool: Pool = Depends(db_pool.get_db),
):
    balances = await db_utils.get_top_channel_balances(
        channel_id=channel,
        offset=offset,
        limit=limit,
        lite=lite,
        orderby=orderby,
        pool=pool,
    )
    return {"result": balances}


@router.get("/tokens/{channel}", tags=["Deprecated"])
async def get_top_token_balances(
    channel: str,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    lite: bool = True,
    orderby: ChannelEarningsOrderBy = Query(ChannelEarningsOrderBy.TOTAL),
    pool: Pool = Depends(db_pool.get_db),
):
    balances = await db_utils.get_top_channel_earnings(
        channel_id=channel,
        offset=offset,
        limit=limit,
        lite=lite,
        earnings_type=ChannelEarningsType.TOKENS,
        orderby=orderby,
        pool=pool,
    )
    return {"result": balances}


@router.get("/tokens/{channel}/claim", tags=["Tokens"])
async def get_token_claim(channel: str, fid: int, pool: Pool = Depends(db_pool.get_db)):
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


@router.get("/distribution/preview/{channel}", tags=["Distribute Rewards"])
async def get_tokens_distrib_preview(
    channel: str,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    scope: ChannelEarningsScope = Query(ChannelEarningsScope.AIRDROP),
    type: ChannelEarningsType = Query(ChannelEarningsType.TOKENS),
    pool: Pool = Depends(db_pool.get_db),
):
    if type == ChannelEarningsType.TOKENS:
        distributions = await db_utils.get_tokens_distrib_preview(
            channel_id=channel, offset=offset, limit=limit, scope=scope, pool=pool
        )
    elif type == ChannelEarningsType.POINTS:
        if scope == ChannelEarningsScope.AIRDROP:
            raise HTTPException(
                status_code=400,
                detail="Points distribution preview not available for airdrop",
            )
        distributions = await db_utils.get_points_distrib_preview(
            channel_id=channel, offset=offset, limit=limit, pool=pool
        )
    return {"result": distributions}


@router.get("/distribution/overview/{channel}", tags=["Tokens"])
async def get_tokens_distrib_overview(
    channel: str,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
):
    distribribution_stats = await db_utils.get_tokens_distrib_overview(
        channel_id=channel, offset=offset, limit=limit, pool=pool
    )
    return {"result": distribribution_stats}


@router.get("/distribution/details/{channel}", tags=["Tokens"])
async def get_tokens_distrib_details(
    channel: str,
    dist_id: Annotated[int | None, Query()] = None,
    batch_id: Annotated[int | None, Query()] = 1,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
):
    details = await db_utils.get_tokens_distrib_details(
        channel_id=channel,
        dist_id=dist_id,
        batch_id=batch_id,
        offset=offset,
        limit=limit,
        pool=pool,
    )
    return {"result": details}


@router.get("/rankings/{channel}", tags=["Deprecated"])
async def get_top_channel_profiles(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    lite: bool = True,
    pool: Pool = Depends(db_pool.get_db),
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
        pool=pool,
    )
    return {"result": ranks}


@router.get("/rankings/{channel}/stats", tags=["Leaderboard", "Metrics"])
async def get_channel_stats(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get basic statistics about the rankings in a channel. \n
    """
    stats = await db_utils.get_channel_stats(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        pool=pool,
    )
    return {"result": stats}


@router.get("/casts/{channel}/metrics", tags=["Deprecated"])
async def get_channel_cast_metrics(
    channel: str,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get basic metrics about a channel. \n
    """
    metrics = await db_utils.get_channel_cast_metrics(
        channel_id=channel,
        pool=pool,
    )
    result = []
    for m in metrics:
        result.append({"metric": m[0], "value": json.loads(m[1])})
    return {"result": result}


@router.get("/metrics/{channel}/", tags=["Channel Feed", "Metrics"])
async def get_channel_metrics(
    channel: str,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get basic metrics about a channel. \n
    """
    metrics = await db_utils.get_channel_cast_metrics(
        channel_id=channel,
        pool=pool,
    )
    result = []
    for m in metrics:
        result.append({"metric": m[0], "value": json.loads(m[1])})
    if settings.DB_VERSION == DBVersion.EIGEN8:
        # TODO: This is a hack to get follower and member metrics. Pre-compute and store in DB.
        follower_metrics = await db_utils.get_channel_fid_metrics(
            channel_id=channel, fid_type=ChannelFidType.FOLLOWER, pool=pool
        )
        for m in follower_metrics:
            result.append({"metric": m[0], "value": json.loads(m[1])})
        member_metrics = await db_utils.get_channel_fid_metrics(
            channel_id=channel, fid_type=ChannelFidType.MEMBER, pool=pool
        )
        for m in member_metrics:
            result.append({"metric": m[0], "value": json.loads(m[1])})
    return {"result": result}


@router.post("/filter/{channel}/fids", tags=["Leaderboard"])
async def filter_channel_fids(
    channel: str,
    fids: list[int],
    filter: ChannelFidType = Query(ChannelFidType.FOLLOWER),
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Given a list of input fids, return a list of fids
      that are filtered by the given filter. \n
      Example: [1, 2] \n
    Parameter 'filter' is used to indicate if the list should be filtered by followers or members. \n
    By default, filter is 'follower'
    """
    if not (1 <= len(fids) <= 100_000):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100,000 entries"
        )
    results = []
    i = 0
    for batch in batched(fids, settings.FID_BATCH_SIZE):
        logger.info(f"Processing batch {i}")
        filtered_fids = await db_utils.filter_channel_fids(
            channel_id=channel, fids=batch, filter=filter, pool=pool
        )
        results.extend([d['fid'] for d in filtered_fids])
        i += 1
    return {"result": results}


@router.post("/rankings/{channel}/fids", tags=["Deprecated"])
async def get_channel_rank_for_fids(
    # Example: -d '[1, 2]'
    channel: str,
    fids: list[int],
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    lite: bool = True,
    pool: Pool = Depends(db_pool.get_db),
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
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    ranks = await db_utils.get_channel_profile_ranks(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        fids=fids,
        lite=lite,
        pool=pool,
    )
    return {"result": ranks}


@router.post("/rankings/{channel}/handles", tags=["Deprecated"])
async def get_channel_rank_for_handles(
    # Example: -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]'
    channel: str,
    handles: list[str],
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Given a list of input handles, return a list of handles
      that are ranked based on the engagement relationships in the channel
      and scored by Eigentrust algorithm. \n
      Example: ["dwr.eth", "varunsrin.eth"] \n
    """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    # fetch handle-fid pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the handle-fid pairs
    fids = [hf["fid"] for hf in handle_fids]

    ranks = await db_utils.get_channel_profile_ranks(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
        fids=fids,
        lite=False,
        pool=pool,
    )
    return {"result": ranks}


@router.get("/casts/popular/{channel}", tags=["Channel Feed", "Neynar Trending Feed"])
async def get_popular_channel_casts(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=100)] = 25,
    lite: Annotated[bool, Query()] = True,
    provider_metadata: Annotated[str | None, Query()] = None,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get a list of recent casts that are the most popular
      based on Eigentrust scores of fids in the channel. \n
    This API takes optional parameters - offset, limit and lite. \n
    Parameter 'lite' is used to constrain the result to just cast hashes. \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    provider_metadata is a **URI encoded JSON string**
    that contains the following for **Trending Feed**: \n
      { \n
        "feedType": "trending",  \n
        "lookback": "day" | "week" | "month" | "three_months" | "six_months", # week is default \n
        "agg": "sum" | "rms" | "sumsquare", # sum is default \n
        "scoreThreshold": 0.000000001, # 0.000000001 is default \n
        "reactionsThreshold": 0-infinity, # 0 is default \n
        "cutoffPtile": 0-100, # 100 is default \n
        "weights": "L1C0R1Y1", # default \n
        "sortingOrder": "day" | "hour" | "score" | "reactions", # day is default \n
        "timeDecay": "minute" | "hour" | "day" | "never", , # "hour" is default \n
        "normalize": true | false, # true is default \n
        "shuffle": true | false # false is default \n
        "timeoutSecs": 3-30, # 30 is default \n
        "sessionId": "string" # optional field \n
      } \n
    provider_metadata is a **URI encoded JSON string**
      that contains the following for **Popular Feed**: \n
    { \n
        "feedType": "popular",  \n
        "lookback": "day" | "week" | "month" | "three_months" | "six_months", # week is default \n
        "agg": "sum" | "rms" | "sumsquare", # sum is default \n
        "scoreThreshold": 0.000000001, # 0.000000001 is default \n
        "reactionsThreshold": 0-infinity, # 10 is default \n
        "weights": "L1C1R1Y1", # default \n
        "sortingOrder": "day" | "hour" | "score" | "reactions", # score is default \n
        "timeDecay": "minute" | "hour" | "day" | "never", # "never" is default \n
        "normalize": true | false, # true is default \n
        "timeoutSecs": 3-30, # 30 is default \n
        "sessionId": "string" # optional field \n
      } \n
    Parameter 'limit' is used to specify the number of results to return. \n
    By default, offset=0, limit=25, and lite=true
      i.e., returns recent 25 **Trending** casts.
    """
    logger.info(f"get_popular_channel_casts: channel={channel}")
    metadata = None
    if provider_metadata:
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
    else:
        # default this api to Trending because Neynar uses this for Trending
        md_json = {"feedType": "trending"}
        metadata = TrendingFeed.validate(md_json)

    try:
        parsed_weights = Weights.from_str(metadata.weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    logger.info(f"Feed params: {metadata}")

    channel_urls = await db_utils.get_channel_url_for_channel_id(
        channel_id=channel, pool=pool
    )
    if len(channel_urls) == 0:
        raise HTTPException(status_code=404, detail="Channel not found")

    # channel_url = fetch_channel(channel_id=channel)
    channel_url = channel_urls[0]['url']

    if metadata and type(metadata) is PopularFeed:
        if lite:
            casts = await db_utils.get_popular_channel_casts_lite(
                channel_id=channel,
                channel_url=channel_url,
                strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
                max_cast_age=CASTS_AGE[metadata.lookback],
                agg=metadata.agg,
                score_threshold=metadata.score_threshold,
                reactions_threshold=metadata.reactions_threshold,
                weights=parsed_weights,
                time_decay=metadata.time_decay,
                normalize=metadata.normalize,
                offset=offset,
                limit=limit,
                sorting_order=metadata.sorting_order,
                pool=pool,
            )
        else:
            # TODO get rid of the heavy version if all clients are going to come through Neynar
            casts = await db_utils.get_popular_channel_casts_heavy(
                channel_id=channel,
                channel_url=channel_url,
                strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
                max_cast_age=CASTS_AGE[metadata.lookback],
                agg=metadata.agg,
                score_threshold=metadata.score_threshold,
                reactions_threshold=metadata.reactions_threshold,
                weights=parsed_weights,
                time_decay=metadata.time_decay,
                normalize=metadata.normalize,
                offset=offset,
                limit=limit,
                sorting_order=metadata.sorting_order,
                pool=pool,
            )
    elif metadata and type(metadata) is FarconFeed:
        casts = await db_utils.get_trending_channel_casts_lite(
            channel_id=channel,
            channel_url=channel_url,
            channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
            max_cast_age=CASTS_AGE[metadata.lookback],
            agg=metadata.agg,
            score_threshold=metadata.score_threshold,
            reactions_threshold=metadata.reactions_threshold,
            cutoff_ptile=metadata.cutoff_ptile,
            weights=parsed_weights,
            shuffle=metadata.shuffle,
            time_decay=metadata.time_decay,
            normalize=metadata.normalize,
            offset=offset,
            limit=limit,
            sorting_order=metadata.sorting_order,
            pool=pool,
        )
    else:
        # defaults to Trending because Neynar calls this API for Trending Feed
        if lite:
            casts = await db_utils.get_trending_channel_casts_lite_memoized(
                channel_id=channel,
                channel_url=channel_url,
                channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
                max_cast_age=CASTS_AGE[metadata.lookback],
                agg=metadata.agg,
                score_threshold=metadata.score_threshold,
                reactions_threshold=metadata.reactions_threshold,
                cutoff_ptile=metadata.cutoff_ptile,
                weights=parsed_weights,
                shuffle=metadata.shuffle,
                time_decay=metadata.time_decay,
                normalize=metadata.normalize,
                offset=offset,
                limit=limit,
                sorting_order=metadata.sorting_order,
                pool=pool,
            )
        else:
            # TODO get rid of the heavy version if all clients are going to come through Neynar
            casts = await db_utils.get_trending_channel_casts_heavy(
                channel_id=channel,
                channel_url=channel_url,
                channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[rank_timeframe],
                max_cast_age=CASTS_AGE[metadata.lookback],
                agg=metadata.agg,
                score_threshold=metadata.score_threshold,
                reactions_threshold=metadata.reactions_threshold,
                cutoff_ptile=metadata.cutoff_ptile,
                weights=parsed_weights,
                shuffle=metadata.shuffle,
                time_decay=metadata.time_decay,
                normalize=metadata.normalize,
                offset=offset,
                limit=limit,
                sorting_order=metadata.sorting_order,
                pool=pool,
            )

    return {"result": casts}


@router.post("/casts/scores/{channel}", tags=["Channel Feed"])
async def get_channel_casts_scores(
    cast_hashes: list[str],
    channel: str,
    provider_metadata: Annotated[str | None, Query()] = None,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Rank a list of given casts based on Eigentrust scores of fids in the channel. \n
    This API takes 1 optional parameter - provider_metadata. \n
    `provider_metadata` is a **URI encoded JSON string**
      that contains the following defaults for scoring Search results: \n
    { \n
        "scoreType": "search",  \n
        "agg": "sum" | "rms" | "sumsquare", # sum is default \n
        "scoreThreshold": 0.000000001, # 0.000000001 is default \n
        "weights": "L1C1R1Y1", # default \n
        "sortingOrder": "day" | "hour" | "score", # score is default \n
        "timeDecay": "minute" | "hour" | "day" | "never", # "never" is default \n
        "normalize": true | false, # true is default \n
      } \n
    provider_metadata is a **URI encoded JSON string**
      that contains the following defaultsfor scoring Replies: \n
      { \n
        "scoreType": "reply",  \n
        "agg": "sum" | "rms" | "sumsquare", # sum is default \n
        "scoreThreshold": 0.000000001, # 0.000000001 is default \n
        "weights": "L1C1R1Y1", # default \n
        "sortingOrder": "day" | "hour" | "score" | "reactions"| "recent", # recent is default \n
        "timeDecay": "minute" | "hour" | "day" | "never", , # "never" is default \n
        "normalize": true | false, # true is default \n
      } \n
    By default, `provider_metadata` is Search.
    """
    if not (1 <= len(cast_hashes) <= 1_000):
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )

    metadata = None
    if provider_metadata:
        # Example: %7B%22scoreType%22%3A%22popular%22%2C%22timeframe%22%3A%22month%22%7D
        md_str = urllib.parse.unquote(provider_metadata)
        logger.info(f"Provider metadata: {md_str}")
        try:
            metadata = ScoresMetadata.validate_json(md_str)
        except ValidationError as e:
            logger.error(f"Error while validating provider metadata: {e}")
            logger.error(f"errors(): {e.errors()}")
            raise HTTPException(
                status_code=400,
                detail=f"Error while validating provider metadata: {e.errors()}",
            )
    else:
        # default this api to Search
        md_json = {"scoreType": "search"}
        metadata = SearchScores.validate(md_json)

    logger.info(f"Feed params: {metadata}")
    cast_hashes = [bytes.fromhex(cast_hash[2:]) for cast_hash in cast_hashes]

    casts = await db_utils.get_channel_casts_scores_lite(
        cast_hashes=cast_hashes,
        channel_id=channel,
        channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[
            ChannelRankingsTimeframe.SIXTY_DAYS
        ],
        agg=metadata.agg,
        score_threshold=metadata.score_threshold,
        weights=Weights.from_str(metadata.weights),
        time_decay=metadata.time_decay,
        normalize=metadata.normalize,
        sorting_order=metadata.sorting_order,
        pool=pool,
    )
    return {"result": casts}


@router.get("/casts/daily/{channel}", tags=["Deprecated"])
async def get_trending_casts(
    channel: str,
    channel_strategy: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    max_cast_age: Annotated[int | None, Query(ge=0, le=30)] = 1,
    agg: Annotated[
        ScoreAgg | None,
        Query(
            description="Define the aggregation function" " - `rms`, `sumsquare`, `sum`"
        ),
    ] = ScoreAgg.SUM,
    weights: Annotated[str | None, Query()] = 'L1C0R1Y1',
    time_decay: Annotated[bool, Query()] = True,
    normalize: Annotated[bool, Query()] = True,
    offset: Annotated[int | None, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=0, le=5000)] = 100,
    sorting_order: Annotated[SortingOrder, Query()] = SortingOrder.SCORE,
    pool: Pool = Depends(db_pool.get_db),
):
    if time_decay:
        time_decay = CastsTimeDecay.HOUR
    else:
        time_decay = CastsTimeDecay.NEVER
    try:
        weights = Weights.from_str(weights)
    except:
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )
    casts = await db_utils.get_trending_channel_casts_heavy(
        channel_id=channel,
        channel_url=fetch_channel(channel_id=channel),
        channel_strategy=CHANNEL_RANKING_STRATEGY_NAMES[channel_strategy],
        max_cast_age=f"{max_cast_age} days",
        agg=agg,
        score_threshold=0.000000001,
        reactions_threshold=0,
        cutoff_ptile=100,
        weights=weights,
        shuffle=False,
        time_decay=time_decay,
        normalize=normalize,
        offset=offset,
        limit=limit,
        sorting_order=sorting_order,
        pool=pool,
    )

    return {"result": casts}


@router.get("/experiments/degen/casts", tags=["Deprecated"])
async def get_popular_casts_from_degen_graph(
    agg: Annotated[
        ScoreAgg | None,
        Query(
            description="Define the aggregation function" " - `rms`, `sumsquare`, `sum`"
        ),
    ] = ScoreAgg.SUMSQUARE,
    weights: Annotated[str | None, Query()] = 'L1C10R5Y1',
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=10000)] = 100,
    sorting_order: Annotated[SortingOrder, Query()] = SortingOrder.SCORE,
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
        raise HTTPException(
            status_code=400, detail="Weights should be of the form 'LxxCxxRxx'"
        )

    casts = await db_utils.get_popular_degen_casts(
        agg=agg,
        weights=weights,
        offset=offset,
        limit=limit,
        sorting_order=sorting_order,
        pool=pool,
    )

    return {"result": casts}


@router.get("/followers/{channel}", tags=["Deprecated"])
async def get_top_channel_followers(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=500000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
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
        pool=pool,
    )
    return {"result": followers}


@router.post("/holders/{channel}/fids", tags=["Leaderboard"])
async def get_leaderboard_rank_for_fids(
    # Example: -d '[1, 2]'
    channel: str,
    fids: list[int],
    orderby: ChannelEarningsOrderBy = Query(ChannelEarningsOrderBy.TOTAL, alias="type"),
    pool: Pool = Depends(db_pool.get_db),
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
        raise HTTPException(
            status_code=400, detail="Input should have between 1 and 100 entries"
        )
    # TODO replace this with a materialized view or some other cache
    # WARNING - very inefficient and only works for now because channel leaderboards are small
    holders = await db_utils.get_top_channel_holders(
        channel_id=channel,
        strategy_name=CHANNEL_RANKING_STRATEGY_NAMES[
            ChannelRankingsTimeframe.SIXTY_DAYS
        ],
        orderby=orderby,
        offset=0,
        limit=100000,
        pool=pool,
    )
    result = []
    for idx, holder in enumerate(holders, start=1):
        if holder["fid"] in fids:
            result.append({**holder, "order_rank": idx})
    return {"result": result}


@router.get("/holders/{channel}", tags=["Leaderboard"])
async def get_top_channel_holders(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    orderby: ChannelEarningsOrderBy = Query(ChannelEarningsOrderBy.TOTAL),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=500000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
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
        pool=pool,
    )
    results = [
        {**f, 'order_rank': idx + offset} for idx, f in enumerate(followers, start=1)
    ]
    return {"result": results}


@router.get("/repliers/{channel}", tags=["Deprecated"])
async def get_top_channel_repliers(
    channel: str,
    rank_timeframe: ChannelRankingsTimeframe = Query(
        ChannelRankingsTimeframe.SIXTY_DAYS
    ),
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=500000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
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
        pool=pool,
    )
    return {"result": followers}


@router.get("/trending", tags=["Trending Channels"])
async def get_trending_channels(
    lookback: ChannelTimeframe = Query(ChannelTimeframe.WEEK),
    rank_threshold: Annotated[
        int | None, Query(alias="rankThreshold", le=100000)
    ] = 10000,
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=100)] = 25,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get a list of trending channels
      based on Eigentrust rankings of fids. \n
    This API takes optional parameters - lookback, rankThreshold, offset and limit. \n
    Parameter 'lookback' is used to specify how far back to look for casts.\n
    Parameter 'rankThreshold' is used to specify
      the minimum rank for an fid's activity to be considered. \n
    Parameter 'offset' is used to specify how many results to skip
      and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    By default, lookback='week, rankThreshold=10000, offset=0, and limit=25
      i.e., returns recent 25 popular casts.
    """

    channels = await db_utils.get_trending_channels(
        max_cast_age=PARENT_CASTS_AGE[lookback],
        rank_threshold=rank_threshold,
        offset=offset,
        limit=limit,
        pool=pool,
    )
    return {"result": channels}

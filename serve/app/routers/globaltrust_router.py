from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..models.graph_model import GraphType
from ..models.score_model import QueryType, EngagementType
from ..dependencies import db_pool, db_utils

router = APIRouter(tags=["Global OpenRank Scores"])


@router.get("/following/rankings")
async def get_top_following_profiles(
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        query_type: Annotated[QueryType, Query()] = QueryType.LITE,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids based on the follows relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
  This API takes two optional parameters - offset and limit. \n
  By default, limit is 100 and offset is 0 i.e., returns top 100 fids.
  """
    ranks = await db_utils.get_top_profiles(strategy_id=GraphType.following.value,
                                            offset=offset,
                                            limit=limit,
                                            pool=pool,
                                            query_type=query_type)

    if query_type == 'superlite':
        converted_ranks = {'fids': [record['fid'] for record in ranks]}
        return {"result": converted_ranks}
    return {"result": ranks}


@router.get("/engagement/rankings")
async def get_top_engagement_profiles(
        engagement_type: Annotated[EngagementType, Query()] = EngagementType.V1Engagement,
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=1000)] = 100,
        query_type: Annotated[QueryType, Query()] = QueryType.LITE,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Get a list of fids based on the engagement relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
  This API takes two optional parameters - offset and limit. \n
  By default, limit is 100 and offset is 0 i.e., returns top 100 fids.
  """
    if engagement_type == 'v1_engagement':
        strategy_id = GraphType.engagement.value
    elif engagement_type == 'v3_engagement':
        strategy_id = GraphType.v3engagement.value

    ranks = await db_utils.get_top_profiles(strategy_id=strategy_id,
                                            offset=offset,
                                            limit=limit,
                                            pool=pool,
                                            query_type=query_type)
    if query_type == 'superlite':
        converted_ranks = {'fids': [record['fid'] for record in ranks]}
        return {"result": converted_ranks}
    return {"result": ranks}


@router.post("/following/fids")
async def get_following_rank_for_fids(
        fids: Annotated[list[int], Body(
            title="Farcaster IDs",
            description="A list of FIDs.",
            examples=[
                [1, 2, 3]
            ]
        )],
        lite: Annotated[bool, Query()] = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input fids, return a list of fids
    that are ranked based on the follows relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
    Example: [1, 2] \n
  """
    if not (1 <= len(fids) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    ranks = await db_utils.get_profile_ranks(strategy_id=GraphType.following.value,
                                             fids=fids,
                                             pool=pool,
                                             lite=lite)
    return {"result": ranks}


@router.post("/following/handles")
async def get_following_rank_for_handles(
        handles: Annotated[list[str], Body(
            title="Handles",
            description="A list of handles.",
            examples=[
                [
                    "farcaster.eth",
                    "varunsrin.eth",
                    "farcaster",
                    "v"
                ]
            ]
        )],
        lite: Annotated[bool, Query()] = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input handles, return a list of fids
    that are ranked based on the follows relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
    Example: ["dwr.eth", "varunsrin.eth"] \n
  """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    # fetch handle-fid pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the handle-fid pairs
    fids = [hf["fid"] for hf in handle_fids]

    ranks = await db_utils.get_profile_ranks(strategy_id=GraphType.following.value,
                                             fids=fids,
                                             pool=pool,
                                             lite=lite)
    return {"result": ranks}


@router.post("/engagement/fids")
async def get_engagement_rank_for_fids(
        fids: Annotated[list[int], Body(
            title="Farcaster IDs",
            description="A list of FIDs.",
            examples=[
                [1, 2, 3]
            ]
        )],
        engagement_type: Annotated[EngagementType, Query()] = EngagementType.V1Engagement,
        lite: Annotated[bool, Query()] = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input fids, return a list of fids
    that are ranked based on the engagement relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
    Example: [1, 2] \n
  """
    if not (1 <= len(fids) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    if engagement_type == 'v1_engagement':
        strategy_id = GraphType.engagement.value
    elif engagement_type == 'v3_engagement':
        strategy_id = GraphType.v3engagement.value

    ranks = await db_utils.get_profile_ranks(strategy_id=strategy_id,
                                             fids=fids,
                                             pool=pool,
                                             lite=lite)
    return {"result": ranks}


@router.post("/engagement/handles")
async def get_engagement_rank_for_handles(
        handles: Annotated[list[str], Body(
            title="Handles",
            description="A list of handles.",
            examples=[
                [
                    "farcaster.eth",
                    "varunsrin.eth",
                    "farcaster",
                    "v"
                ]
            ]
        )],
        engagement_type: Annotated[EngagementType, Query()] = EngagementType.V1Engagement,
        lite: Annotated[bool, Query()] = True,
        pool: Pool = Depends(db_pool.get_db)
):
    """
  Given a list of input fids, return a list of fids
    that are ranked based on the engagement relationships in the Fracaster network
    and scored by Eigentrust algorithm. \n
    Example: ["dwr.eth", "varunsrin.eth"] \n
  """
    if not (1 <= len(handles) <= 100):
        raise HTTPException(status_code=400, detail="Input should have between 1 and 100 entries")
    # fetch handle-fid pairs for given handles
    handle_fids = await db_utils.get_unique_fid_metadata_for_handles(handles, pool)

    # extract fids from the handle-fid pairs
    fids = [hf["fid"] for hf in handle_fids]
    print(fids)

    if engagement_type == 'v1_engagement':
        strategy_id = GraphType.engagement.value
    elif engagement_type == 'v3_engagement':
        strategy_id = GraphType.v3engagement.value

    ranks = await db_utils.get_profile_ranks(strategy_id=strategy_id,
                                             fids=fids,
                                             pool=pool,
                                             lite=lite)
    return {"result": ranks}

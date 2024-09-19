from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from ..dependencies import graph, db_pool, db_utils

router = APIRouter(tags=["User Labels"])


@router.post("/labels/global/top_casters")
async def get_top_global_casters(
        offset: Annotated[int | None, Query()] = 0,
        limit: Annotated[int | None, Query(le=500)] = 1000,
        pool: Pool = Depends(db_pool.get_db)):
    """
    Get the top global casters
    This API takes optional parameters -
    limit upto 10000 fids
    """

    top_casters = await db_utils.get_top_casters(offset=offset,
                                                 limit=limit,
                                                 pool=pool)
    return {"result": top_casters}

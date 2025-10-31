from typing import Annotated, Optional

from asyncpg.pool import Pool
from fastapi import APIRouter, Depends, Header, Query

from ..dependencies import db_pool, db_utils

router = APIRouter(tags=["User Labels (Requires API Key)"])


def unused(*_):
    pass


@router.get("/labels/global/top_casters")
async def get_top_global_casters(
    x_api_key: Optional[str] = Header(None),  # used only for swagger ui
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get the top global casters
    This API takes optional parameters -
    offset and limit
    Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    Header 'x-api-key' is used to authenticate the user. Please contact hello@karma3labs.com or <a href="https://t.me/Karma3Labs" target=_blank>https://t.me/Karma3Labs</a> to get the trial API key. \n
    """

    unused(x_api_key)
    top_casters = await db_utils.get_top_casters(offset=offset, limit=limit, pool=pool)
    return {"result": top_casters}


@router.get("/labels/global/top_spammers")
async def get_top_global_spammers(
    x_api_key: Optional[str] = Header(None),  # used only for swagger ui
    offset: Annotated[int | None, Query()] = 0,
    limit: Annotated[int | None, Query(le=1000)] = 100,
    pool: Pool = Depends(db_pool.get_db),
):
    """
    Get the top global spammers
    This API takes optional parameters -
    offset and limit
    Parameter 'offset' is used to specify how many results to skip
    and can be useful for paginating through results. \n
    Parameter 'limit' is used to specify the number of results to return. \n
    Header 'x-api-key' is used to authenticate the user. Please contact hello@karma3labs.com or <a href="https://t.me/Karma3Labs" target=_blank>https://t.me/Karma3Labs</a> to get the trial API key. \n
    """

    unused(x_api_key)
    top_spammers = await db_utils.get_top_spammers(
        offset=offset, limit=limit, pool=pool
    )
    return {"result": top_spammers}

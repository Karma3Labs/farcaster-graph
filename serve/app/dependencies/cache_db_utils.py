import json

from loguru import logger
from asyncpg.pool import Pool


async def set_homefeed_for_fid(
    fid: int, cids: list[str], offset: int, cache_pool: Pool
):

    session_data = {"api": "homefeed", "cids": cids, "offset": offset}
    session_value = json.dumps(session_data)
    key = f"session:{fid}"

    # TODO update db using cache_pool
    pass


async def get_homefeed_for_fid(fid: int, cache_pool: Pool) -> dict:

    key = f"session:{fid}"

    # TODO get cached data from db using cache_pool

    return {"cids": [], "offset": 0}

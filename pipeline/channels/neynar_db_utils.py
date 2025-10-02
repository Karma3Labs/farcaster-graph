import logging
from typing import List
import asyncpg
from channels.channel_db_utils import fetch_rows


async def get_profile_details(logger: logging.Logger, pool: asyncpg.Pool, fids: List[int]):
    sql_query = """
select * from neynarv3.profiles where fid = ANY($1);
    """
    rows = await fetch_rows(fids, logger=logger, sql_query=sql_query, pool=pool)
    return {row["fid"]: row for row in rows}


async def get_cast_content(logger: logging.Logger, pool: asyncpg.Pool, cast_hash: str):
    hash_bytes = bytes.fromhex(cast_hash[2:])
    sql_query = """
select * from neynarv3.casts where hash=$1;
    """
    return await fetch_rows(hash_bytes, logger=logger, sql_query=sql_query, pool=pool)

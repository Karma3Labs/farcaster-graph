import logging
from typing import List
import asyncpg
from channels.channel_db_utils import fetch_rows


async def get_profile_details(logger: logging.Logger, pg_dsn: str, fids: List[int]):
    pool = await asyncpg.create_pool(pg_dsn, min_size=1, max_size=5)
    sql_query = """
select * from neynarv3.profiles where fid = ANY($1);
    """
    rows = await fetch_rows(fids, logger=logger, sql_query=sql_query, pool=pool)
    return {row["fid"]: row for row in rows}


async def get_cast_content(logger: logging.Logger, pg_dsn: str, cast_hash: str):
    pool = await asyncpg.create_pool(pg_dsn, min_size=1, max_size=5)

    hash_bytes = bytes.fromhex(cast_hash[2:])
    sql_query = """
select * from neynarv3.casts where hash=$1;
    """
    return await fetch_rows(hash_bytes, logger=logger, sql_query=sql_query, pool=pool)

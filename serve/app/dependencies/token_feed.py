import base64
import datetime
import json
import urllib.parse
from typing import Dict, List, Optional

import requests
from asyncpg.pool import Pool
from loguru import logger

from ..config import settings
from datetime import timedelta
from ..models.feed_model import SortingOrder, ScoreAgg, Weights, CastsTimeDecay
from .db_utils import get_fip2_cast_hashes, get_top_token_casts


async def get_token_feed(
    int_chain_id: int,
    token_address: str,
    cursor: str,
    token_symbol: str,
    viewer_fid: str,
    pool: Pool,
    sorting_order: SortingOrder = SortingOrder.RECENT,
):
    if sorting_order == SortingOrder.POPULAR or sorting_order == SortingOrder.SCORE:
        offset = 0
        if cursor:
            try:
                offset = int(cursor)
            except ValueError:
                pass  # invalid cursor, start from 0

        limit = 25
        # Default settings for top feed
        # TODO: Make these configurable via query params if needed
        rows = await get_top_token_casts(
            chain_id=int_chain_id,
            token_address=token_address,
            token_symbol=token_symbol,
            agg=ScoreAgg.SUM,
            weights=Weights.from_str("L1C1R1Y1"),
            score_threshold=0.000000001,
            max_cast_age=timedelta(days=7), # 7 days lookback as discussed
            time_decay=CastsTimeDecay.NEVER, # No decay for "top" in window? Or maybe HOUR? Let's stick to raw score for "Top".
            offset=offset,
            limit=limit,
            pool=pool,
        )

        # Extract hashes
        cast_hashes = [row["cast_hash"] for row in rows]
        
        if not cast_hashes:
            return {
                "casts": [],
                "next": {"cursor": None},
            }

        # Fetch full casts from Neynar to get consistent schema
        hashes_str = ",".join(cast_hashes)
        neynar_url = f"casts?casts={hashes_str}&viewer_fid={viewer_fid}"
        neynar_resp = neynar_get(neynar_url)
        
        final_casts = []
        if neynar_resp.ok:
            neynar_data = neynar_resp.json()            
            fetched_casts = neynar_data.get("result", {}).get("casts", [])
            
            # Create a dict for O(1) lookup
            casts_map = {c["hash"]: c for c in fetched_casts}
            
            # Reconstruct list in the original sorted order
            for h in cast_hashes:
                if h in casts_map:
                    final_casts.append(casts_map[h])
        else:
            logger.error(f"Failed to fetch casts from Neynar: {neynar_resp.text}")
            pass

        next_cursor = None
        if len(rows) == limit:
            next_cursor = str(offset + limit)

        return {
            "casts": final_casts,
            "next": {"cursor": next_cursor},
        }

    # get neynar FIP 2 feed.
    url = f"feed/parent_urls/?with_recasts=true&limit=25&parent_urls=eip155%3A{int_chain_id}%2Ferc20%3A{token_address.lower()}"
    before_ts = None
    if cursor:
        url += f"&cursor={cursor}"
        before_ts = get_ts_in_search_query_format(get_ts_from_cursor(cursor))

    result = neynar_get(url).json()
    fip2_casts_next_cursor = result["next"]["cursor"]
    fip2_casts = result["casts"]
    after_ts = None
    if fip2_casts_next_cursor:
        after_ts = get_ts_in_search_query_format(
            get_ts_from_cursor(fip2_casts_next_cursor)
        )

    # get search casts
    search_casts, search_casts_next_cursor = get_search_casts(
        f"${token_symbol}", viewer_fid, before_ts, after_ts
    )

    all_casts = remove_duplicates(search_casts + fip2_casts)

    await flag_fip2_casts(all_casts, pool)

    # sort the casts
    all_casts.sort(key=lambda x: x["timestamp"], reverse=True)

    if search_casts_next_cursor and fip2_casts_next_cursor:
        # We fetch only 1 page from both and data up to the common cursor.
        fip2_ts = get_ts_in_search_query_format(
            get_ts_from_cursor(fip2_casts_next_cursor)
        )
        search_ts = get_ts_in_search_query_format(
            get_ts_from_cursor(search_casts_next_cursor)
        )
        if fip2_ts > search_ts:
            min_ts = search_ts
            next_cursor = search_casts_next_cursor
        else:
            min_ts = fip2_ts
            next_cursor = fip2_casts_next_cursor

        # cut extra casts.
        stripped_casts = []
        for cast in all_casts:
            if cast["timestamp"] >= min_ts:
                stripped_casts.append(cast)

        return {
            "casts": stripped_casts,
            "next": {"cursor": next_cursor},
        }

    return {
        "casts": all_casts,
        "next": {"cursor": fip2_casts_next_cursor or search_casts_next_cursor},
    }


def remove_duplicates(casts: List[dict]):
    all_casts = []
    seen_hahes = set()
    for cast in casts:
        if cast["hash"] in seen_hahes:
            continue

        all_casts.append(cast)
        seen_hahes.add(cast["hash"])

    return all_casts


async def flag_fip2_casts(casts: List[dict], pool: Pool):
    cast_hashes = list(set(cast["hash"] for cast in casts))

    fip2_cast_hashes = await get_fip2_cast_hashes(
        cast_hashes=cast_hashes, chain_id=8453, pool=pool
    )

    fip2_hashes_set = {record["hash"] for record in fip2_cast_hashes}

    for cast in casts:
        if cast["hash"] in fip2_hashes_set:
            cast["cast_type"] = "fip2"


def get_search_casts(
    search_str: str, viewer_fid: str, before_ts: Optional[str], after_ts: Optional[str]
):
    # fip2 feed is empty if `after_ts` is None, we only serve search feed going forward.

    final_search_str = f"{search_str}"
    if after_ts:
        final_search_str += f" + after:{after_ts}"
    if before_ts:
        final_search_str += f" + before:{before_ts}"

    url = f"cast/search?q={final_search_str}&mode=literal&sort_type=algorithmic&viewer_fid={viewer_fid}"
    neynar_resp = neynar_get(url)
    if neynar_resp.ok:
        data = neynar_resp.json()["result"]
    else:
        logger.warning(f"failed to fetch search casts {neynar_resp.text} ({url=}")
        return []

    return data["casts"], data["next"]["cursor"]


def neynar_get(path: str):
    return requests.get(
        f"https://api.neynar.com/v2/farcaster/{path}",
        headers={"x-api-key": settings.NEYNAR_API_KEY},
    )


def decode_cursor(base64_cursor: str) -> Dict:
    return json.loads(base64.b64decode(urllib.parse.unquote(base64_cursor)).decode())


def get_ts_from_cursor(base64_cursor: str) -> datetime.datetime:
    timestamp = json.loads(
        base64.b64decode(urllib.parse.unquote(base64_cursor)).decode()
    )["timestamp"]
    return datetime.datetime.strptime(timestamp[:-1], "%Y-%m-%d %H:%M:%S.%f")


def get_ts_in_search_query_format(timestamp: datetime.datetime):
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S")

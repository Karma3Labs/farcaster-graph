import base64
import datetime
import json
import urllib.parse
from typing import Dict, List, Optional

import requests
from loguru import logger

from ..config import settings


async def get_token_feed(
    int_chain_id: int,
    token_address: str,
    cursor: str,
    token_symbol: str,
    viewer_fid: str,
):
    # get neynar FIP 2 feed.
    url = f"feed/parent_urls/?with_recasts=true&limit=25&parent_urls=eip155%3A{int_chain_id}%2Ferc20%3A{token_address.lower()}"
    before_ts = None
    if cursor:
        url += f"&cursor={cursor}"
        before_ts = get_ts_in_search_query_format(get_ts_from_cursor(cursor))

    result = neynar_get(url).json()
    fip2_casts_next_cursor = result['next']['cursor']
    fip2_casts = result['casts']
    add_cast_type(fip2_casts, 'fip2')
    after_ts = None
    if fip2_casts_next_cursor:
        after_ts = get_ts_in_search_query_format(
            get_ts_from_cursor(fip2_casts_next_cursor)
        )

    # get search casts
    search_casts, search_casts_next_cursor = get_search_casts(
        f"${token_symbol}", viewer_fid, before_ts, after_ts
    )
    add_cast_type(search_casts, 'search')

    all_casts = search_casts + fip2_casts
    # sort the casts
    all_casts.sort(key=lambda x: x['timestamp'], reverse=True)

    if search_casts_next_cursor and fip2_casts_next_cursor:
        # We fetch only 1 page from both and data upto common cursor.
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
            if cast['timestamp'] >= min_ts:
                stripped_casts.append(cast)

        return {
            "casts": stripped_casts,
            "next": {"cursor": next_cursor},
        }

    return {
        "casts": all_casts,
        "next": {"cursor": fip2_casts_next_cursor or search_casts_next_cursor},
    }


def add_cast_type(casts: List[dict], cast_type: str):
    for cast in casts:
        cast['cast_type'] = cast_type


def get_search_casts(
    search_str: str, viewer_fid: str, before_ts: Optional[str], after_ts: Optional[str]
):
    # fip2 feed is empty if `after_ts` is None, we only serve search feed going forward.

    final_search_str = f"{search_str}"
    if after_ts:
        final_search_str += f" + after:{after_ts}"
    if before_ts:
        final_search_str += f" + before:{before_ts}"

    neynar_resp = neynar_get(
        f"cast/search?q={final_search_str}&mode=literal&sort_type=algorithmic&viewer_fid={viewer_fid}"
    )
    if neynar_resp.ok:
        data = neynar_resp.json()['result']
    else:
        logger.warning(f"failed to fetch search casts {neynar_resp.text}")
        return []

    return data['casts'], data['next']['cursor']


def neynar_get(path: str):
    return requests.get(
        f"https://api.neynar.com/v2/farcaster/{path}",
        headers={'x-api-key': settings.NEYNAR_API_KEY},
    )


def decode_cursor(base64_cursor: str) -> Dict:
    return json.loads(base64.b64decode(urllib.parse.unquote(base64_cursor)).decode())


def get_ts_from_cursor(base64_cursor: str) -> datetime.datetime:
    timestamp = json.loads(
        base64.b64decode(urllib.parse.unquote(base64_cursor)).decode()
    )['timestamp']
    return datetime.datetime.strptime(timestamp[:-1], '%Y-%m-%d %H:%M:%S.%f')


def get_ts_in_search_query_format(timestamp: datetime.datetime):
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S')

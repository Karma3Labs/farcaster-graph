from loguru import logger
from typing import Dict, Optional, Self
import requests
import json
import base64, urllib.parse
import datetime
from ..config import settings


async def get_token_feed(
    int_chain_id: int,
    token_address: str,
    cursor: str,
    token_symbol: str,
    viewer_fid: str,
):
    # TODO: Handle the case of empty in either of the feeds!

    # get neynar FIP 2 feed.
    url = f"feed/parent_urls/?with_recasts=true&limit=25&parent_urls=eip155%3A{int_chain_id}%2Ferc20%3A{token_address.lower()}"
    before_ts = None
    if cursor:
        url += f"&cursor={cursor}"
        before_ts = get_ts_in_search_query_format(get_ts_from_cursor(cursor))

    result = neynar_get(url).json()
    decode_cursor = result['next']['cursor']
    fip2_casts = result['casts']
    after_ts = get_ts_in_search_query_format(get_ts_from_cursor(decode_cursor))

    # get search casts
    search_casts = search_all_casts(f"${token_symbol}", viewer_fid, before_ts, after_ts)

    all_casts = search_casts + fip2_casts
    # sort the casts
    all_casts.sort(key=lambda x: x['timestamp'], reverse=True)

    return {"casts": all_casts, "next": {"cursor": decode_cursor}}


def search_all_casts(search_str: str, viewer_fid: str, before_ts: str, after_ts: str):
    final_search_str = f"{search_str} + after:{after_ts}"
    if before_ts:
        final_search_str += f" before:{before_ts}"

    next_cursor = None
    search_casts = []
    while True:
        neynar_resp = neynar_get(
            f"cast/search?q={final_search_str}&mode=literal&cursor={next_cursor if next_cursor else ''}&sort_type=algorithmic&viewer_fid={viewer_fid}"
        )
        if neynar_resp.ok:
            data = neynar_resp.json()['result']
        else:
            logger.warning(f"failed to fetch search casts {neynar_resp.text}")
            return []

        next_cursor = data['next']['cursor']
        search_casts += data['casts']

        logger.info(
            f"Fetched a page of search results, getting next page with cursor {next_cursor}"
        )

        if not next_cursor:
            break

    return search_casts


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

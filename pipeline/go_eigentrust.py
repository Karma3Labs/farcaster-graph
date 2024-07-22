import time
from config import settings
from loguru import logger
import pandas as pd
import numpy as np
import requests
from typing import List, Dict

def get_scores(lt_df: pd.DataFrame, pt_ids: List[int]) -> List[Dict[str, float]]:
    start_time = time.perf_counter()

    # Filter out entries where i == j
    lt_df = lt_df[lt_df['i'] != lt_df['j']]

    # Convert pt_ids to set for better performance in membership checks
    pt_ids_set = set(pt_ids)

    stacked = lt_df[['i', 'j']].stack()
    pseudo_id, orig_id = stacked.factorize()

    # Create a new DataFrame to avoid modifying the original
    pseudo_df = pd.DataFrame({
        'i': pseudo_id[::2],
        'j': pseudo_id[1::2],
        'v': lt_df['v'].values
    })

    pt_len = len(pt_ids_set)
    pretrust = [{'i': orig_id.get_loc(fid), 'v': 1 / pt_len} for fid in pt_ids_set]
    max_pt_id = len(orig_id)

    localtrust = pseudo_df.to_dict(orient="records")
    max_lt_id = len(orig_id)

    logger.debug(f"max_lt_id: {max_lt_id}, localtrust size: {len(localtrust)},"
                f" max_pt_id: {max_pt_id}, pretrust size: {len(pretrust)}")
    logger.trace(f"localtrust: {localtrust}")
    logger.trace(f"pretrust: {pretrust}")

    scores = go_eigentrust(
        pretrust=pretrust,
        max_pt_id=max_pt_id,
        localtrust=localtrust,
        max_lt_id=max_lt_id
    )
    logger.trace(f"scores: {scores}")

    # Debug log to check the range of indices in scores
    # max_index_in_scores = max(score['i'] for score in scores)
    # logger.info(f"Max index in scores: {max_index_in_scores}, Size of orig_id: {len(orig_id)}")

    i_scores = [{'i': int(orig_id[score['i']]), 'v': score['v']} for score in scores if score['i'] < len(orig_id)]
    logger.debug(f"get_scores took {time.perf_counter() - start_time} secs for {len(i_scores)} scores")
    return i_scores

def go_eigentrust(
    pretrust: List[Dict[str, float]],
    max_pt_id: np.int32,
    localtrust: List[Dict[str, float]],
    max_lt_id: np.int32,
) -> List[Dict[str, float]]:
    start_time = time.perf_counter()

    lt_len_before = len(localtrust)
    localtrust = [x for x in localtrust if x['i'] != x['j']]
    lt_len_after = len(localtrust)
    if lt_len_before != lt_len_after:
        logger.info(f"dropped {lt_len_before - lt_len_after} records with i == j")

    req = {
        "pretrust": {
            "scheme": 'inline',
            "size": int(max_pt_id) + 1,  # np.int64 doesn't serialize; cast to int
            "entries": pretrust,
        },
        "localTrust": {
            "scheme": 'inline',
            "size": int(max_lt_id) + 1,  # np.int64 doesn't serialize; cast to int
            "entries": localtrust,
        },
        "alpha": settings.EIGENTRUST_ALPHA,
        # "epsilon": settings.EIGENTRUST_EPSILON,
        # "max_iterations": settings.EIGENTRUST_MAX_ITER,
        # "flatTail": settings.EIGENTRUST_FLAT_TAIL
    }

    logger.debug(f"calling go_eigentrust")
    response = requests.post(f"{settings.GO_EIGENTRUST_URL}/basic/v1/compute",
                             json=req,
                             headers={
                                 'Accept': 'application/json',
                                 'Content-Type': 'application/json'
                             },
                             timeout=settings.GO_EIGENTRUST_TIMEOUT_MS)

    if response.status_code != 200:
        logger.error(f"Server error: {response.status_code}:{response.reason}")
        raise Exception(f"Server error: {response.status_code}:{response.reason}")
    trustscores = response.json()['entries']
    logger.debug(f"go_eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores")
    return trustscores

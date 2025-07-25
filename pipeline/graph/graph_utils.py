import time

import pandas as pd
import polars as pl
from loguru import logger
from niquests import Session
from niquests.adapters import HTTPAdapter
from niquests.exceptions import RequestException
from urllib3.util import Retry

import go_eigentrust
from config import settings

# Create a session with a connection pool
retries = Retry(
    total=5,
    backoff_factor=10,  # retry in 10s, 20s, 40s, 80s, 160s
    status_forcelist=[502, 503, 504],
    allowed_methods={"GET"},
)
session = Session(retries=retries)
adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount("http://", adapter)
session.mount("https://", adapter)


def get_direct_edges_df(
    fid: int,
    df: pd.DataFrame,
    max_neighbors: int,
) -> pd.DataFrame:
    # WARNING we are operating on a shared dataframe...
    # ...inplace=False by default, explicitly setting here for emphasis
    out_df = df[df["i"] == fid].sort_values(by=["v"], ascending=False, inplace=False)[
        :max_neighbors
    ]
    return out_df


def get_k_degree_neighbors(
    fid: int,
    limit: int,
    k: int,
) -> list[int]:
    payload = {"fid": int(fid), "k": k, "limit": limit}
    try:
        response = session.get(
            settings.PERSONAL_IGRAPH_URLPATH, params=payload, timeout=600
        )
        response.raise_for_status()
        logger.trace(f"{response.json()}")
        return response.json()
    except RequestException as e:
        logger.error(f"Error fetching k-degree neighbors for FID {fid}: {str(e)}")
        return []


def get_k_degree_scores(
    fid: int,
    k_minus_list: list[int],
    localtrust_df: pl.DataFrame,
    limit: int,
    k: int,
    process_label: str,
) -> list[int]:
    start_time = time.perf_counter()
    k_fid_list = get_k_degree_neighbors(fid, limit, k)
    logger.debug(
        f"{process_label}iGraph took {time.perf_counter() - start_time} secs"
        f" for {len(k_fid_list)} k-{k} neighbors"
    )
    if len(k_fid_list) > 0:
        # include all previous degree neighbors when calculating go-eigentrust
        k_fid_list.extend(k_minus_list)
        k_fid_list.extend([fid])
        logger.trace(f"{process_label}k_fid_list:{k_fid_list}")

        start_time = time.perf_counter()
        k_df = localtrust_df.filter(
            (pl.col("i").is_in(k_fid_list)) & (pl.col("j").is_in(k_fid_list))
        )

        logger.debug(
            f"{process_label}k-{k} Polars took {time.perf_counter() - start_time} secs for {len(k_df)} edges"
        )

        if len(k_df) > 0:
            k_df_pd = k_df.to_pandas()
            k_scores = go_eigentrust.get_scores(k_df_pd, [fid])
            del k_df_pd

            # filter out previous degree neighbors
            k_scores = [score for score in k_scores if score["i"] not in k_minus_list]

            return k_scores
    return []


def cleanup():
    session.close()


# Example usage (you can remove or modify this as needed)
if __name__ == "__main__":
    try:
        # Your main code here
        pass
    finally:
        cleanup()

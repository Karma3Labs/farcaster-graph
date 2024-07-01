from enum import Enum
import logging

import utils, db_utils
from timer import Timer
from .channel_queries import IJVSql, IVSql

import pandas as pd

# global variable to cache fetching from db
_pretrust_toptier_df: pd.DataFrame = None


def _fetch_pt_toptier_df(logger: logging.Logger, pg_dsn: str) -> pd.DataFrame:
    global _pretrust_toptier_df

    if _pretrust_toptier_df is not None:
        return _pretrust_toptier_df

    _pretrust_toptier_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, IVSql.PRETRUST_TOP_TIER)
    return _pretrust_toptier_df


def _fetch_interactions_df(logger: logging.Logger, pg_dsn: str, channel_url: str) -> pd.DataFrame:
    query = IJVSql.COMBINED_INTERACTION
    _channel_interactions_df: pd.DataFrame = None

    with Timer(name="combined_interactions"):
        _channel_interactions_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query, channel_url)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    return _channel_interactions_df

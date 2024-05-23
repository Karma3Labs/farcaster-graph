from enum import Enum
import logging

import utils, db_utils
from timer import Timer
from .channel_queries import IJVSql, IVSql
from . import go_eigentrust
from config import settings

import pandas as pd

# global variable to cache fetching from db
_pretrust_toptier_df: pd.DataFrame = None


def _fetch_pt_toptier_df(logger: logging.Logger, pg_dsn: str) -> pd.DataFrame:
    global _pretrust_toptier_df

    if _pretrust_toptier_df is not None:
        return _pretrust_toptier_df

    _pretrust_toptier_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, IVSql.PRETRUST_TOP_TIER)
    return _pretrust_toptier_df


def _fetch_interactions_df(logger: logging.Logger, pg_dsn: str, channel: str) -> pd.DataFrame:
    query = IJVSql.LIKES_NEYNAR % channel
    _channel_interactions_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    query = IJVSql.REPLIES % channel
    with Timer(name="merge_replies"):
        _channel_interactions_df = _channel_interactions_df.merge(
            db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
            how='outer',
            left_on=['i', 'j'], right_on=['i', 'j'],
            indicator=False)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    query = IJVSql.MENTIONS_NEYNAR % channel
    with Timer(name="merge_mentions"):
        _channel_interactions_df = _channel_interactions_df.merge(
            db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
            how='outer',
            left_on=['i', 'j'], right_on=['i', 'j'],
            indicator=False)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    query = IJVSql.RECASTS_NEYNAR % channel
    with Timer(name="merge_recasts"):
        _channel_interactions_df = _channel_interactions_df.merge(
            db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
            how='outer',
            left_on=['i', 'j'], right_on=['i', 'j'],
            indicator=False)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    query = IJVSql.FOLLOWS_NEYNAR
    with Timer(name="merge_follows"):
        _channel_interactions_df = _channel_interactions_df.merge(
            db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
            how='outer',
            left_on=['i', 'j'], right_on=['i', 'j'],
            indicator=False)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="l1rep1rec1m1"):
        _channel_interactions_df['l1rep1rec1m1'] = \
            _channel_interactions_df.loc[:,
            ['likes_v',
             'replies_v',
             'mentions_v',
             'recasts_v',
             'follows_v']].sum(axis=1)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="l1rep6rec3m12"):
        _channel_interactions_df['l1rep6rec3m12'] = \
            _channel_interactions_df['likes_v'].fillna(0) \
            + (_channel_interactions_df['replies_v'].fillna(0) * 6.0) \
            + (_channel_interactions_df['recasts_v'].fillna(0) * 3.0) \
            + (_channel_interactions_df['mentions_v'].fillna(0) * 12.0) \
            + _channel_interactions_df['follows_v'].fillna(0)
    logger.info(utils.df_info_to_string(_channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    return _channel_interactions_df

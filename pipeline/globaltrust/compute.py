from enum import Enum
import logging

import utils
import db_utils
import go_eigentrust
from timer import Timer
from .queries import IJVSql, IVSql
from config import settings

import pandas as pd
import gc

# global variable to cache fetching from db
_pretrust_toptier_df: pd.DataFrame = None
_interactions_df: pd.DataFrame = None

class Strategy(Enum):
  FOLLOWING = ('follows', 1)
  ENGAGEMENT = ('engagement', 3)
  ACTIVITY = ('activity', 5)

def _fetch_pt_toptier_df(logger: logging.Logger, pg_dsn: str, target_date: str) -> pd.DataFrame:
  global _pretrust_toptier_df

  if _pretrust_toptier_df is not None:
    return _pretrust_toptier_df

  where_clause = "" if target_date is None else f"insert_ts <= '{target_date}'::date + interval '1 day'"
  query = db_utils.construct_query(IVSql.PRETRUST_TOP_TIER, where_clause=where_clause)
  _pretrust_toptier_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
  return _pretrust_toptier_df

def _fetch_interactions_df(logger: logging.Logger, pg_dsn: str, target_date: str = None) -> pd.DataFrame:
  global _interactions_df

  if _interactions_df is not None:
    return _interactions_df

  # All the tables referred to in this function def have the same timestamp field
  where_clause = "" if target_date is None else f"timestamp <= '{target_date}'::date + interval '1 day'"

  query = db_utils.construct_query(IJVSql.LIKES, where_clause=where_clause)
  _interactions_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  query = db_utils.construct_query(IJVSql.REPLIES, where_clause=where_clause)
  with Timer(name="merge_replies"):
    _interactions_df = _interactions_df.merge(
                        db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
                        how='outer',
                        left_on=['i','j'], right_on=['i','j'],
                        indicator=False)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  query = db_utils.construct_query(IJVSql.MENTIONS, where_clause=where_clause)
  with Timer(name="merge_mentions"):
    _interactions_df = _interactions_df.merge(
                        db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
                        how='outer',
                        left_on=['i','j'], right_on=['i','j'],
                        indicator=False)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  query = db_utils.construct_query(IJVSql.RECASTS, where_clause=where_clause)
  with Timer(name="merge_recasts"):
    _interactions_df = _interactions_df.merge(
                        db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
                        how='outer',
                        left_on=['i','j'], right_on=['i','j'],
                        indicator=False)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  query = db_utils.construct_query(IJVSql.FOLLOWS, where_clause=where_clause)
  with Timer(name="merge_follows"):
    _interactions_df = _interactions_df.merge(
                        db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query),
                        how='outer',
                        left_on=['i','j'], right_on=['i','j'],
                        indicator=False)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="l1rep1rec1m1"):
    _interactions_df['l1rep1rec1m1'] = \
                        _interactions_df.loc[:,
                          ['likes_v',
                           'replies_v',
                           'mentions_v',
                           'recasts_v',
                           'follows_v']].sum(axis=1)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="l1rep6rec3m12"):
    _interactions_df['l1rep6rec3m12'] = \
                        _interactions_df['likes_v'].fillna(0) \
                          + (_interactions_df['replies_v'].fillna(0) * 6.0) \
                          + (_interactions_df['recasts_v'].fillna(0) * 3.0) \
                          + (_interactions_df['mentions_v'].fillna(0) * 12.0) \
                          + _interactions_df['follows_v'].fillna(0)
  logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
  utils.log_memusage(logger)

  return _interactions_df


def lt_gt_for_strategy(
    logger: logging.Logger,
    pg_dsn: str,
    strategy: Strategy,
    target_date: str = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
  with Timer(name=f"{strategy}"):
    intx_df = _fetch_interactions_df(logger, pg_dsn, target_date)
    match strategy:
      case Strategy.FOLLOWING:
        pt_df = _fetch_pt_toptier_df(logger, pg_dsn, target_date)
        lt_df = \
          intx_df[intx_df['follows_v'].notna()] \
            [['i','j','follows_v']].rename(columns={'follows_v':'v'})
      case Strategy.ENGAGEMENT:
        pt_df = _fetch_pt_toptier_df(logger, pg_dsn, target_date)
        lt_df = \
          intx_df[intx_df['l1rep6rec3m12'] > 0] \
            [['i','j','l1rep6rec3m12']] \
              .rename(columns={'l1rep6rec3m12':'v'})
      case Strategy.ACTIVITY:
        pt_df = _fetch_pt_toptier_df(logger, pg_dsn, target_date)
        lt_df = \
          intx_df[intx_df['follows_v'].notna()] \
            [['i','j','l1rep1rec1m1']] \
              .rename(columns={'l1rep1rec1m1':'v'})
      case _:
        raise Exception(f"Unknown Strategy: {strategy}")
    # end of match

    logger.info(f"{strategy} Pre-Trust: {utils.df_info_to_string(pt_df, with_sample=True)}")
    logger.info(f"{strategy} LocalTrust: {utils.df_info_to_string(lt_df, with_sample=True)}")
    utils.log_memusage(logger)

    # Filter out entries where i == j
    lt_df = lt_df[lt_df['i'] != lt_df['j']]

    with Timer(name=f"prep_eigentrust_{strategy}"):
      localtrust = lt_df.to_dict(orient="records")
      max_lt_id = max(lt_df['i'].max(), lt_df['j'].max())
      pretrust = pt_df.to_dict(orient="records")
      max_pt_id = pt_df['i'].max()

    globaltrust = go_eigentrust.go_eigentrust(pretrust,
                                              max_pt_id,
                                              localtrust,
                                              max_lt_id
                                              )
    logger.info(f"go_eigentrust returned {len(globaltrust)} entries")
    
    # manually call garbage collector to free up localtrust immediately
    utils.log_memusage(logger)
    logger.debug("calling garbage collector to free up localtrust immediately")
    del localtrust
    del pretrust
    gc.collect()
    utils.log_memusage(logger)

    with Timer(name=f"post_eigentrust_{strategy}"):
      gt_df = pd.DataFrame.from_records(globaltrust)
    logger.info(utils.df_info_to_string(gt_df, with_sample=True))

    # manually call garbage collector to free up globaltrust immediately
    utils.log_memusage(logger)
    del globaltrust
    logger.debug("calling garbage collector to free up globaltrust immediately")
    gc.collect()
    utils.log_memusage(logger)
  # end Timer
  return (lt_df, gt_df)
# compute_lt_gt_for_strategy

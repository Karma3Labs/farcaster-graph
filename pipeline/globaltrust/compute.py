import gc
import logging
from enum import Enum
from pathlib import Path

import pandas as pd

import db_utils
import go_eigentrust
import utils
from config import settings
from timer import Timer

from .queries import IJVSql, IVSql

# global variable to cache fetching from db
_pretrust_toptier_df: pd.DataFrame = None
_interactions_df: pd.DataFrame = None


class Strategy(Enum):
    FOLLOWING = ("follows", 1)
    ENGAGEMENT = ("engagement", 3)  # Follows1Likes1Replies6Recasts3Mentions12
    # ACTIVITY = ('activity', 5)
    V3ENGAGEMENT = (
        "v3engagement",
        9,
    )  # Follows1Likes1or2Replies3or4Recasts6or7Mentions12or13
    GRAPH_90DV3 = ("graph_90dv3", 11)  # Similar to V3 but with 90d window


def _fetch_pt_toptier_df(
    logger: logging.Logger, pg_dsn: str, strategy_id: int
) -> pd.DataFrame:
    global _pretrust_toptier_df

    if _pretrust_toptier_df is not None:
        return _pretrust_toptier_df
    query = db_utils.construct_pretrust_query(
        IVSql.PRETRUST_TOP_TIER, strategy_id=strategy_id
    )
    _pretrust_toptier_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
    return _pretrust_toptier_df


def _fetch_interactions_df(
    logger: logging.Logger, pg_dsn: str, target_date: str = None, interval: int = 0
) -> pd.DataFrame:
    global _interactions_df

    if _interactions_df is not None:
        return _interactions_df

    # All the tables referred to in this function def have the same timestamp field
    where_clause = (
        f"timestamp >= now() - interval '{interval} days'"
        if interval > 0
        else (
            f"timestamp <= '{target_date}'::date + interval '1 day'"
            if target_date is not None
            else None
        )
    )

    query = db_utils.construct_query(IJVSql.LIKES, where_clause=where_clause)
    logger.info(f"Fetching likes: {query}")
    l_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
    logger.info(utils.df_info_to_string(l_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="merge_replies"):
        query = db_utils.construct_query(IJVSql.REPLIES, where_clause=where_clause)
        logger.info(f"Fetching replies: {query}")
        replies_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
        lr_df = l_df.merge(
            replies_df,
            how="outer",
            left_on=["i", "j"],
            right_on=["i", "j"],
            indicator=False,
        )
        # outer join will create new dataframe; explicit del may help reduce memusage
        del replies_df
        del l_df
    logger.info(utils.df_info_to_string(lr_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="merge_mentions"):
        query = db_utils.construct_query(IJVSql.MENTIONS, where_clause=where_clause)
        logger.info(f"Fetching mentions: {query}")
        mentions_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
        lrm_df = lr_df.merge(
            mentions_df,
            how="outer",
            left_on=["i", "j"],
            right_on=["i", "j"],
            indicator=False,
        )
        # outer join will create new dataframe; explicit del may help reduce memusage
        del mentions_df
        del lr_df
    logger.info(utils.df_info_to_string(lrm_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="merge_recasts"):
        query = db_utils.construct_query(IJVSql.RECASTS, where_clause=where_clause)
        logger.info(f"Fetching recasts: {query}")
        recasts_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
        lrmc_df = lrm_df.merge(
            recasts_df,
            how="outer",
            left_on=["i", "j"],
            right_on=["i", "j"],
            indicator=False,
        )
        # outer join will create new dataframe; explicit del may help reduce memusage
        del recasts_df
        del lrm_df
    logger.info(utils.df_info_to_string(lrmc_df, with_sample=True))
    utils.log_memusage(logger)

    with Timer(name="merge_follows"):
        query = db_utils.construct_query(IJVSql.FOLLOWS, where_clause=where_clause)
        logger.info(f"Fetching follows: {query}")
        follows_df = db_utils.ijv_df_read_sql_tmpfile(pg_dsn, query)
        _interactions_df = lrmc_df.merge(
            follows_df,
            how="outer",
            left_on=["i", "j"],
            right_on=["i", "j"],
            indicator=False,
        )
        # outer join will create new dataframe; explicit del may help reduce memusage
        del follows_df
        del lrmc_df
    logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    # We don't compute Activity strategy anymore.
    # Save compute time by not computing this column.
    # with Timer(name="l1rep1rec1m1"):
    #   _interactions_df['l1rep1rec1m1'] = \
    #                       _interactions_df.loc[:,
    #                         ['likes_v',
    #                          'replies_v',
    #                          'mentions_v',
    #                          'recasts_v',
    #                          'follows_v']].sum(axis=1)
    # logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
    # utils.log_memusage(logger)

    # for Enagement Strategy
    with Timer(name="l1rep6rec3m12"):
        _interactions_df["l1rep6rec3m12"] = (
            _interactions_df["likes_v"].fillna(0)
            + (_interactions_df["replies_v"].fillna(0) * 6.0)
            + (_interactions_df["recasts_v"].fillna(0) * 3.0)
            + (_interactions_df["mentions_v"].fillna(0) * 12.0)
            + _interactions_df["follows_v"].fillna(0)
        )
    logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    # for EngagementV2 strategy
    with Timer(name="l1rep3rec6m12"):
        _interactions_df["l1rep3rec6m12"] = (
            _interactions_df["likes_v"].fillna(0)
            + (_interactions_df["replies_v"].fillna(0) * 3.0)
            + (_interactions_df["recasts_v"].fillna(0) * 6.0)
            + (_interactions_df["mentions_v"].fillna(0) * 12.0)
            + _interactions_df["follows_v"].fillna(0)
        )
    logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    # for EngagementV3 strategy we boost all inteactions by 1
    with Timer(name="fboostedl1rep3rec6m12"):
        _interactions_df["fboostedl1rep3rec6m12"] = (
            _interactions_df["likes_v"].fillna(0)
            + (_interactions_df["replies_v"].fillna(0) * 3.0)
            + (_interactions_df["recasts_v"].fillna(0) * 6.0)
            + (_interactions_df["mentions_v"].fillna(0) * 12.0)
            + _interactions_df["follows_v"].fillna(0)
            + (
                _interactions_df["follows_v"].fillna(0)
                * (
                    _interactions_df["replies_v"].fillna(0)
                    + _interactions_df["recasts_v"].fillna(0)
                    + _interactions_df["mentions_v"].fillna(0)
                )
            )
        )
    logger.info(utils.df_info_to_string(_interactions_df, with_sample=True))
    utils.log_memusage(logger)

    # drop unused columns to recover some memory
    _interactions_df.drop(
        columns=["likes_v", "replies_v", "recasts_v", "mentions_v"], inplace=True
    )

    # Filter out entries where i == j
    _interactions_df = _interactions_df[_interactions_df["i"] != _interactions_df["j"]]

    return _interactions_df


def localtrust_for_strategy(
    logger: logging.Logger,
    pg_dsn: str,
    strategy: Strategy,
    target_date: str = None,
    interval: int = 0,
) -> pd.DataFrame:
    with Timer(name=f"{strategy}"):
        intx_df = _fetch_interactions_df(logger, pg_dsn, target_date, interval)
        match strategy:
            case Strategy.FOLLOWING:
                lt_df = intx_df[intx_df["follows_v"].notna()][
                    ["i", "j", "follows_v"]
                ].rename(columns={"follows_v": "v"})
            case Strategy.ENGAGEMENT:
                lt_df = intx_df[intx_df["l1rep6rec3m12"] > 0][
                    ["i", "j", "l1rep6rec3m12"]
                ].rename(columns={"l1rep6rec3m12": "v"})
            case Strategy.V3ENGAGEMENT | Strategy.GRAPH_90DV3:
                lt_df = intx_df[intx_df["fboostedl1rep3rec6m12"] > 0][
                    ["i", "j", "fboostedl1rep3rec6m12"]
                ].rename(columns={"fboostedl1rep3rec6m12": "v"})
            # case Strategy.ACTIVITY:
            #   lt_df = \
            #     intx_df[intx_df['follows_v'].notna()] \
            #       [['i','j','l1rep1rec1m1']] \
            #         .rename(columns={'l1rep1rec1m1':'v'})
            case _:
                raise Exception(f"Unknown Strategy: {strategy}")
        # end of match
        logger.info(
            f"{strategy} LocalTrust: {utils.df_info_to_string(lt_df, with_sample=True)}"
        )
        utils.log_memusage(logger)
    # end Timer
    return lt_df


# end localtrust_for_strategy


def pretrust_for_strategy(
    logger: logging.Logger, pg_dsn: str, strategy: Strategy
) -> pd.DataFrame:

    with Timer(name=f"{strategy}"):
        match strategy:
            case Strategy.FOLLOWING:
                pt_df = _fetch_pt_toptier_df(
                    logger, pg_dsn, Strategy.FOLLOWING.value[1]
                )
            case Strategy.ENGAGEMENT:
                pt_df = _fetch_pt_toptier_df(
                    logger, pg_dsn, Strategy.ENGAGEMENT.value[1]
                )
            # case Strategy.ACTIVITY:
            #   pt_df = _fetch_pt_toptier_df(logger, pg_dsn, target_date, Strategy.FOLLOWING.value[1])
            case Strategy.V3ENGAGEMENT:
                pt_df = _fetch_pt_toptier_df(
                    logger, pg_dsn, Strategy.V3ENGAGEMENT.value[1]
                )
            case _:
                raise Exception(f"Unknown Strategy: {strategy}")
        # end of match

        logger.info(
            f"{strategy} Pre-Trust: {utils.df_info_to_string(pt_df, with_sample=True)}"
        )
        utils.log_memusage(logger)
    # end Timer
    return pt_df


# end pretrust_for_strategy


def globaltrust_for_strategy(
    logger: logging.Logger,
    pt_filepath: Path,
    lt_filepath: Path,
    strategy: Strategy,
) -> pd.DataFrame:

    with Timer(name=f"{strategy}"):
        if settings.GO_EIGENTRUST_FILE_MODE:
            with Timer(name="go_eigentrust_from_file"):
                logger.info(f"go_eigentrust_from_file {(pt_filepath, lt_filepath)}")
                globaltrust = go_eigentrust.go_eigentrust_from_file(
                    pt_filepath, lt_filepath
                )
        else:
            with Timer(name=f"prep_eigentrust_{strategy}"):
                # we could have used list(csv.DictReader) but we need the max id
                logger.info(f"reading localtrust from {lt_filepath}")
                lt_df = pd.read_csv(lt_filepath, usecols=["i", "j", "v"])
                logger.info(
                    f"LocalTrust: {utils.df_info_to_string(lt_df, with_sample=True)}"
                )
                logger.info("converting localtrust dataframe to dict")
                localtrust = lt_df.to_dict(orient="records")
                max_lt_id = max(lt_df["i"].max(), lt_df["j"].max())
                logger.info(f"reading pretrust from {pt_filepath}")
                pt_df = pd.read_csv(pt_filepath, usecols=["i", "v"])
                logger.info(
                    f"PreTrust: {utils.df_info_to_string(pt_df, with_sample=True)}"
                )
                logger.info("converting pretrust dataframe to dict")
                pretrust = pt_df.to_dict(orient="records")
                max_pt_id = pt_df["i"].max()

            # manually call garbage collector to free up intermediate pandas objects
            utils.log_memusage(logger)
            logger.info(
                "calling garbage collector to free up intermediate pandas and db objects"
            )
            del lt_df
            del pt_df
            gc.collect()
            utils.log_memusage(logger)

            with Timer(name="go_eigentrust_inline"):
                globaltrust = go_eigentrust.go_eigentrust(
                    pretrust,
                    max_pt_id,
                    localtrust,
                    max_lt_id,
                    settings.GO_EIGENTRUST_URL_ALT,
                )
            # manually call garbage collector to free up localtrust
            utils.log_memusage(logger)
            logger.debug("calling garbage collector to free up localtrust immediately")
            del localtrust
            del pretrust
            gc.collect()
            utils.log_memusage(logger)
        # end if GO_EIGENTRUST_FILE_MODE

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
    return gt_df


# end globaltrust_for_strategy

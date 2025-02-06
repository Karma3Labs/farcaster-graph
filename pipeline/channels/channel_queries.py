import logging

from timer import Timer
import pandas as pd

import utils
import db_utils
from db_utils import SQL


INTERACTIONS_SQL = SQL("COMBINED_INTERACTION", """
    WITH
        excluded_fids AS (
            SELECT
                hidden_fid as fid
            FROM
                cura_hidden_fids
            WHERE
                is_active = true
                AND channel_id = '{channel_id}'
        ),
        likes AS (
            SELECT
                reactions.fid AS i,
                reactions.target_fid AS j,
                COUNT(1) AS likes_v
            FROM
                reactions
            INNER JOIN
                casts ON casts.hash = reactions.target_hash
            LEFT JOIN 
                excluded_fids ON (excluded_fids.fid = reactions.fid)
            WHERE
                reactions.reaction_type = 1
                AND reactions.target_fid IS NOT NULL
                AND reactions.deleted_at IS NULL
                AND casts.root_parent_url = '{channel_url}'
                AND excluded_fids.fid IS NULL
                {r_condition}
            GROUP BY
                reactions.fid, reactions.target_fid
        ),
        replies AS (
            SELECT
                casts.fid AS i,
                casts.parent_fid AS j,
                COUNT(1) AS replies_v
            FROM
                casts
            LEFT JOIN 
                excluded_fids ON (excluded_fids.fid = casts.fid)
            WHERE
                casts.parent_hash IS NOT NULL
                AND casts.root_parent_url = '{channel_url}'
                AND casts.deleted_at IS NULL
                AND excluded_fids.fid IS NULL
                {c_condition}
            GROUP BY
                casts.fid, casts.parent_fid
        ),
        mentions_rows AS (
            SELECT
                casts.fid AS author_fid,
                unnest(casts.mentions) AS mention_fid
            FROM
                casts
            LEFT JOIN 
                excluded_fids ON (excluded_fids.fid = casts.fid)
            WHERE
                casts.root_parent_url = '{channel_url}'
                AND casts.deleted_at IS NULL
                AND excluded_fids.fid IS NULL
                {c_condition}
        ),
        mentions_agg AS (
            SELECT
                author_fid AS i,
                mention_fid AS j,
                COUNT(1) AS mentions_v
            FROM
                mentions_rows
            LEFT JOIN 
                excluded_fids ON (excluded_fids.fid = author_fid)
            WHERE
                excluded_fids.fid IS NULL
            GROUP BY
                author_fid, mention_fid
        ),
        recasts AS (
            SELECT
                reactions.fid AS i,
                reactions.target_fid AS j,
                COUNT(1) AS recasts_v
            FROM
                reactions
            INNER JOIN
                casts ON reactions.target_hash = casts.hash
            LEFT JOIN 
                excluded_fids ON (excluded_fids.fid = reactions.fid)
            WHERE
                reactions.reaction_type = 2
                AND reactions.target_fid IS NOT NULL
                AND reactions.deleted_at IS NULL
                AND casts.root_parent_url = '{channel_url}'
                AND excluded_fids.fid IS NULL
                {r_condition}
            GROUP BY
                reactions.fid, reactions.target_fid
        ),
        unique_pairs AS (
            SELECT DISTINCT i, j
            FROM (
                SELECT i, j FROM likes
                UNION
                SELECT i, j FROM replies
                UNION
                SELECT i, j FROM mentions_agg
                UNION
                SELECT i, j FROM recasts
            ) AS combined_pairs
        ),
        follows AS (
            SELECT
                up.i,
                up.j,
                1 AS follows_v
            FROM
                unique_pairs up
            JOIN
                links ON up.i = links.fid AND up.j = links.target_fid
            WHERE
                links.type = 'follow'
                AND links.deleted_at IS NULL
                {l_condition}
            ORDER BY
                up.i, up.j, follows_v DESC
        )
    SELECT
        COALESCE(likes.i, replies.i, ma.i, recasts.i, follows.i) AS i,
        COALESCE(likes.j, replies.j, ma.j, recasts.j, follows.j) AS j,
        -- COALESCE(likes.likes_v, 0) AS likes_v,
        -- COALESCE(replies.replies_v, 0) AS replies_v,
        -- COALESCE(ma.mentions_v, 0) AS mentions_v,
        -- COALESCE(recasts.recasts_v, 0) AS recasts_v,
        -- COALESCE(follows.follows_v, 0) AS follows_v,
        -- COALESCE(likes.likes_v, 0) + COALESCE(replies.replies_v, 0) + COALESCE(ma.mentions_v, 0) + COALESCE(recasts.recasts_v, 0) + COALESCE(follows.follows_v, 0) AS l1rep1rec1m1,
        COALESCE(likes.likes_v, 0) + (COALESCE(replies.replies_v, 0) * 6.0) + (COALESCE(recasts.recasts_v, 0) * 3.0) + (COALESCE(ma.mentions_v, 0) * 12.0) + COALESCE(follows.follows_v, 0) AS l1rep6rec3m12
    FROM
        likes
    FULL OUTER JOIN
        replies ON likes.i = replies.i AND likes.j = replies.j
    FULL OUTER JOIN
        mentions_agg ma ON likes.i = ma.i AND likes.j = ma.j
    FULL OUTER JOIN
        recasts ON likes.i = recasts.i AND likes.j = recasts.j
    FULL OUTER JOIN
        follows ON likes.i = follows.i AND likes.j = follows.j
    """)


def fetch_interactions_df(
    logger: logging.Logger,
    pg_dsn: str,
    channel_url: str,
    channel_id: str,
    interval: int,
) -> pd.DataFrame:
    query_args = {
        "r_condition": f" AND reactions.timestamp >= now() - interval '{interval} days'" if interval > 0 else "",
        "c_condition": f" AND casts.timestamp >= now() - interval '{interval} days'" if interval > 0 else "",
        "l_condition": f" AND links.timestamp >= now() - interval '{interval} days'" if interval > 0 else "",
        "channel_url": channel_url,
        "channel_id": channel_id
    }
    with Timer(name=f"fetch_interactions_{channel_url}"):
        channel_interactions_df = db_utils.ijv_df_read_sql_tmpfile(
            pg_dsn,
            INTERACTIONS_SQL,
            **query_args,
        )
    logger.info(utils.df_info_to_string(channel_interactions_df, with_sample=True))
    utils.log_memusage(logger)
    return channel_interactions_df

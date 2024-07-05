from db_utils import SQL

class IJVSql(SQL):
    LIKES_NEYNAR = SQL("LIKES_NEYNAR", """
    SELECT r.fid as i, r.target_fid as j, count(1) as likes_v
    FROM reactions r
    INNER JOIN casts c on c.hash = r.target_hash
    WHERE r.reaction_type=1
    AND r.target_fid IS NOT null
    AND c.root_parent_url in ('{channel_url}')
    GROUP BY i, j
    """)
    REPLIES = SQL("REPLIES", """
    SELECT fid as i, parent_fid as j, count(1) as replies_v
    FROM casts
    WHERE parent_hash IS NOT NULL
    AND root_parent_url in ('{channel_url}')
    GROUP by i, j
    """)

    MENTIONS_NEYNAR = SQL("MENTIONS_NEYNAR", """
    WITH mention AS (
        SELECT fid as author_fid, mention as mention_fid
        FROM casts, unnest(casts.mentions) as mention
        WHERE root_parent_url in ('{channel_url}')
    )
    SELECT
        author_fid as i, mention_fid as j, count(1) as mentions_v
    FROM mention
    GROUP BY i, j
    """)

    RECASTS_NEYNAR = SQL("RECASTS_NEYNAR", """
    SELECT r.fid as i, r.target_fid as j, count(1) as recasts_v
    FROM reactions r
    INNER JOIN casts c on r.target_hash = c.hash
    WHERE r.reaction_type=2
    AND r.target_fid IS NOT NULL
    AND c.root_parent_url in ('{channel_url}')
    GROUP BY i, j
    """)

    FOLLOWS_NEYNAR = SQL("FOLLOWS_NEYNAR", """
    SELECT
        fid as i,
        target_fid as j,
        1 as follows_v
    FROM links
    WHERE type = 'follow'::text
    ORDER BY i, j, follows_v desc
    """)

    COMBINED_INTERACTION = SQL("COMBINED_INTERACTION", """
    WITH
        likes_neynar AS (
            SELECT
                r.fid AS i,
                r.target_fid AS j,
                COUNT(1) AS likes_v
            FROM
                reactions r
            INNER JOIN
                casts c ON c.hash = r.target_hash
            WHERE
                r.reaction_type = 1
                AND r.target_fid IS NOT NULL
                AND c.root_parent_url = '{channel_url}'
            GROUP BY
                r.fid, r.target_fid
        ),
        replies AS (
            SELECT
                fid AS i,
                parent_fid AS j,
                COUNT(1) AS replies_v
            FROM
                casts
            WHERE
                parent_hash IS NOT NULL
                AND root_parent_url = '{channel_url}'
            GROUP BY
                fid, parent_fid
        ),
        mentions_neynar AS (
            SELECT
                fid AS author_fid,
                unnest(casts.mentions) AS mention_fid
            FROM
                casts
            WHERE
                root_parent_url = '{channel_url}'
        ),
        mentions_agg AS (
            SELECT
                author_fid AS i,
                mention_fid AS j,
                COUNT(1) AS mentions_v
            FROM
                mentions_neynar
            GROUP BY
                author_fid, mention_fid
        ),
        recasts_neynar AS (
            SELECT
                r.fid AS i,
                r.target_fid AS j,
                COUNT(1) AS recasts_v
            FROM
                reactions r
            INNER JOIN
                casts c ON r.target_hash = c.hash
            WHERE
                r.reaction_type = 2
                AND r.target_fid IS NOT NULL
                AND c.root_parent_url = '{channel_url}'
            GROUP BY
                r.fid, r.target_fid
        ),
        unique_pairs AS (
            SELECT DISTINCT i, j
            FROM (
                SELECT i, j FROM likes_neynar
                UNION
                SELECT i, j FROM replies
                UNION
                SELECT i, j FROM mentions_agg
                UNION
                SELECT i, j FROM recasts_neynar
            ) AS combined_pairs
        ),
        follows_neynar AS (
            SELECT
                up.i,
                up.j,
                1 AS follows_v
            FROM
                unique_pairs up
            JOIN
                links l ON up.i = l.fid AND up.j = l.target_fid
            WHERE
                l.type = 'follow'
            ORDER BY
                up.i, up.j, follows_v DESC
        )
    SELECT
        COALESCE(ln.i, r.i, ma.i, rn.i, fn.i) AS i,
        COALESCE(ln.j, r.j, ma.j, rn.j, fn.j) AS j,
        COALESCE(ln.likes_v, 0) AS likes_v,
        COALESCE(r.replies_v, 0) AS replies_v,
        COALESCE(ma.mentions_v, 0) AS mentions_v,
        COALESCE(rn.recasts_v, 0) AS recasts_v,
        COALESCE(fn.follows_v, 0) AS follows_v,
        COALESCE(ln.likes_v, 0) + COALESCE(r.replies_v, 0) + COALESCE(ma.mentions_v, 0) + COALESCE(rn.recasts_v, 0) + COALESCE(fn.follows_v, 0) AS l1rep1rec1m1,
        COALESCE(ln.likes_v, 0) + (COALESCE(r.replies_v, 0) * 6.0) + (COALESCE(rn.recasts_v, 0) * 3.0) + (COALESCE(ma.mentions_v, 0) * 12.0) + COALESCE(fn.follows_v, 0) AS l1rep6rec3m12
    FROM
        likes_neynar ln
    FULL OUTER JOIN
        replies r ON ln.i = r.i AND ln.j = r.j
    FULL OUTER JOIN
        mentions_agg ma ON ln.i = ma.i AND ln.j = ma.j
    FULL OUTER JOIN
        recasts_neynar rn ON ln.i = rn.i AND ln.j = rn.j
    FULL OUTER JOIN
        follows_neynar fn ON ln.i = fn.i AND ln.j = fn.j
    """)

class IVSql(SQL):
    PRETRUST_TOP_TIER = SQL("PRETRUST_TOP_TIER", """
    WITH pt_size AS (
      select count(*) as ct from pretrust
      where insert_ts=(select max(insert_ts) from pretrust)
    )
    SELECT fid as i, 1/ct::numeric as v
    FROM pretrust, pt_size
    WHERE insert_ts=(select max(insert_ts) from pretrust)
    """)
    PRETRUST_POPULAR = SQL("PRETRUST_POPULAR", """
    SELECT
        c.fid AS i,
        1/20::numeric as v
    FROM
        reactions r
        INNER JOIN casts c ON c.hash = r.target_cast_hash
        INNER JOIN user_data u ON c.fid = u.fid AND u.type = 6
    WHERE
        r.created_at >= current_timestamp - interval '7' day
    GROUP BY
        c.fid
    ORDER BY
        COUNT(*) DESC
    LIMIT 20
    """)
    PRETRUST_OG = SQL("PRETRUST_OG", """
    SELECT
        distinct fid as i,
        1/11::numeric as v
    FROM user_data
    WHERE
        value in ('dwr.eth', 'varunsrin.eth', 'balajis.eth',
                  'vitalik.eth','ccarella.eth','tim',
                  'lesgreys.eth','linda','ace',
                  'vm','cdixon.eth')
        AND type=6
    """)

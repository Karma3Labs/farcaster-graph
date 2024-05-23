from enum import Enum


class SQL(Enum): pass


class IJVSql(SQL):
    LIKES_NEYNAR = """
    SELECT r.fid as i, r.target_fid as j, count(1) as likes_v 
    FROM reactions r
    INNER JOIN casts c on c.hash = r.target_hash 
    WHERE r.reaction_type=1
    AND r.target_fid IS NOT null
    AND c.root_parent_url in ('%s')
    GROUP BY i, j
    """
    REPLIES = """
    SELECT fid as i, parent_fid as j, count(1) as replies_v 
    FROM casts
    WHERE parent_hash IS NOT NULL
    AND root_parent_url in ('%s')
    GROUP by i, j
    """

    MENTIONS_NEYNAR = """
    WITH mention AS (
        SELECT fid as author_fid, mention as mention_fid 
        FROM casts, unnest(casts.mentions) as mention
        WHERE root_parent_url in ('%s')
    )
    SELECT 
        author_fid as i, mention_fid as j, count(1) as mentions_v
    FROM mention
    GROUP BY i, j
    """

    RECASTS_NEYNAR = """
    SELECT r.fid as i, r.target_fid as j, count(1) as recasts_v 
    FROM reactions r
    INNER JOIN casts c on r.target_hash = c.hash
    WHERE r.reaction_type=2
    AND r.target_fid IS NOT NULL
    AND c.root_parent_url in ('%s')
    GROUP BY i, j
    """

    FOLLOWS_NEYNAR = """
    SELECT 
        fid as i, 
        target_fid as j,
        1 as follows_v
    FROM links 
    WHERE type = 'follow'::text
    ORDER BY i, j, follows_v desc
    """


class IVSql(SQL):
    PRETRUST_TOP_TIER = """
    WITH pt_size AS (
      select count(*) as ct from pretrust 
      where insert_ts=(select max(insert_ts) from pretrust)
    ) 
    SELECT fid as i, 1/ct::numeric as v
    FROM pretrust, pt_size
    WHERE insert_ts=(select max(insert_ts) from pretrust)
    """
    PRETRUST_POPULAR = """
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
    """
    PRETRUST_OG = """
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
    """

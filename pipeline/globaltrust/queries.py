from casts.interactions import InteractionType
from db_utils import SQL


class IJVSql:
    LIKES_ALL = SQL(
        "LIKES_ALL",
        f"""
    SELECT source as i, target as j, value as likes_v 
    FROM public.k3l_farcaster_interactions 
    WHERE interaction_type={InteractionType.LIKE.value}
    """,
    )
    LIKES = SQL(
        "LIKES",
        """
    SELECT reactions.fid as i, reactions.target_fid as j, count(1) as likes_v 
    FROM neynarv3.reactions 
    INNER JOIN neynarv3.fids ON fids.fid = reactions.target_fid
    WHERE reaction_type=1
    AND reactions.target_fid IS NOT NULL
    {condition}
    GROUP BY i, j
    """,
    )
    REPLIES_ALL = SQL(
        "REPLIES_ALL",
        f"""
    SELECT source as i, target as j, value as replies_v 
    FROM public.k3l_farcaster_interactions 
    WHERE interaction_type={InteractionType.REPLY.value}
    """,
    )
    REPLIES = SQL(
        "REPLIES",
        """
    SELECT fid as i, parent_fid as j, count(1) as replies_v 
    FROM neynarv3.casts
    WHERE parent_hash IS NOT NULL
    {condition}
    GROUP by i, j
    """,
    )
    MENTIONS = SQL(
        "MENTIONS",
        """
    WITH mention AS (
			SELECT fid as author_fid, mention as mention_fid, timestamp
			FROM neynarv3.casts, unnest(casts.mentions) as mention
		)
		SELECT 
			author_fid as i, mention_fid as j, count(1) as mentions_v
		FROM mention
    INNER JOIN neynarv3.fids ON fids.fid = mention.mention_fid
    {condition}
		GROUP BY i, j
    """,
    )
    RECASTS = SQL(
        "RECASTS",
        """
    SELECT reactions.fid as i, reactions.target_fid as j, count(1) as recasts_v 
    FROM neynarv3.reactions 
    INNER JOIN neynarv3.fids ON fids.fid = reactions.target_fid
    WHERE reaction_type=2
    AND reactions.target_fid IS NOT NULL
    {condition}
    GROUP BY i, j
    """,
    )
    FOLLOWS = SQL(
        "FOLLOWS",
        """
    SELECT 
        links.fid as i, 
        links.target_fid as j,
        1 as follows_v
    FROM links 
    INNER JOIN neynarv3.fids ON fids.fid = links.target_fid
    WHERE type = 'follow'::text
    {condition}
    ORDER BY i, j, follows_v desc
    """,
    )


class IVSql:
    PRETRUST_TOP_TIER = SQL(
        "PRETRUST_TOP_TIER",
        """
    WITH pt_size AS (
      select count(*) as ct from pretrust_v2 
      where insert_ts=(select max(insert_ts) from pretrust_v2 where strategy_id = {strategy})
      and strategy_id = {strategy}
    ) 
    SELECT fid as i, 1/ct::numeric as v
    FROM pretrust_v2, pt_size
    WHERE insert_ts=(select max(insert_ts) from pretrust_v2 where strategy_id = {strategy})
    AND strategy_id = {strategy}
    """,
    )
    PRETRUST_POPULAR = SQL(
        "PRETRUST_POPULAR",
        """
    SELECT
			c.fid AS i, 
      1/20::numeric as v
		FROM
			neynarv3.reactions r
			INNER JOIN neynarv3.casts c ON c.hash = r.target_hash
		WHERE
			r.created_at >= current_timestamp - interval '7' day
		GROUP BY
			c.fid
		ORDER BY
			COUNT(*) DESC
		LIMIT 20
    """,
    )
    PRETRUST_OG = SQL(
        "PRETRUST_OG",
        """
    SELECT 
			distinct fid as i,
      1/11::numeric as v
		FROM neynarv3.profiles
		WHERE 
			username in ('dwr.eth', 'varunsrin.eth', 'balajis.eth', 
    				  'vitalik.eth','ccarella.eth','tim',
					  'lesgreys.eth','linda','ace',
					  'vm','cdixon.eth')
    """,
    )

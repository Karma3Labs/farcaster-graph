from enum import Enum

class SQL(Enum): pass

class IJVSql(SQL):
  LIKES = """
    SELECT fid as i, target_cast_fid as j, count(1) as likes_v 
    FROM reactions 
    WHERE type=1
    AND fid < 10000
    GROUP BY i, j
    """
  REPLIES = """
    SELECT fid as i, parent_fid as j, count(1) as replies_v 
    FROM casts
    WHERE parent_hash IS NOT NULL
    AND fid < 10000
    GROUP by i, j
    """
  MENTIONS = """
    WITH mention AS (
			SELECT fid as author_fid, mention.value as mention_fid 
			FROM casts, json_array_elements_text(casts.mentions) as mention
		)
		SELECT 
			author_fid as i, mention_fid as j, count(1) as mentions_v
		FROM mention
        WHERE author_fid < 10000
		GROUP BY i, j
    """
  RECASTS = """
    SELECT fid as i, target_cast_fid as j, count(1) as reacts_v 
    FROM reactions 
    WHERE type=2
    AND fid < 10000
    GROUP BY i, j
    """
  FOLLOWS = """
    SELECT 
        follower_fid as i, 
        following_fid as j,
        1 as follows_v
    FROM mv_follow_links 
    WHERE follower_fid < 10000
    ORDER BY i, j, follows_v desc
    """
  
class IVSql(SQL):
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
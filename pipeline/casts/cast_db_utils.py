import logging

from timer import Timer

import psycopg2
import psycopg2.extras

@Timer(name="insert_cast_action")
def insert_cast_action(logger: logging.Logger, pg_dsn: str, interval_hours: int):
  insert_sql = f"""
    INSERT INTO k3l_cast_action
    WITH max_cast_action AS (
      SELECT 
        coalesce(max(created_at), now() - interval '5 days')  as max_at
      FROM k3l_cast_action
    )
    SELECT
      casts.fid as fid,
      casts.hash as cast_hash,
      1 as casted,
      0 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts, max_cast_action
    WHERE 
    	casts.timestamp > now() - interval '5 days'
      AND
      casts.created_at 
        BETWEEN max_cast_action.max_at 
        AND max_cast_action.max_at + interval '{interval_hours} hours'
    UNION ALL
    SELECT
      casts.fid as fid,
      casts.parent_hash as cast_hash,
      0 as casted,
      1 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts,
      casts.created_at
    FROM casts CROSS JOIN max_cast_action
    WHERE 
    	casts.timestamp > now() - interval '5 days'
      AND
      casts.parent_hash IS NOT NULL
      AND
      casts.created_at 
        BETWEEN max_cast_action.max_at 
          AND max_cast_action.max_at + interval '{interval_hours} hours'
    UNION ALL
    SELECT 
      reactions.fid as fid,
      reactions.target_hash as cast_hash,
      0 as casted,
      0 as replied,
      CASE reactions.reaction_type WHEN 2 THEN 1 ELSE 0 END as recasted,
      CASE reactions.reaction_type WHEN 1 THEN 1 ELSE 0 END as liked,
      reactions.timestamp as action_ts,
      reactions.created_at
    FROM reactions CROSS JOIN max_cast_action
    WHERE 
    	reactions.timestamp > now() - interval '5 days'
      AND
      reactions.created_at 
        BETWEEN max_cast_action.max_at 
          AND max_cast_action.max_at + interval '{interval_hours} hours'
      AND
      reactions.reaction_type IN (1,2)
      AND 
      reactions.target_hash IS NOT NULL
    ORDER BY created_at ASC
    ON CONFLICT(cast_hash, fid, action_ts)
    DO NOTHING -- expect duplicates because of between clause
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {insert_sql}")
      cursor.execute(insert_sql)


import logging

from timer import Timer

import psycopg2
import psycopg2.extras


@Timer(name="insert_fid_cast_action")
def insert_fid_cast_action(logger: logging.Logger, pg_dsn: str, limit: int):
  insert_sql = f"""
    INSERT INTO k3l_fid_cast_action
    WITH max_cast_action AS (
      SELECT 
        coalesce(max(action_ts),now() - interval '90 days')  as max_ts
      FROM k3l_fid_cast_action
    )
    SELECT
      casts.fid as fid,
      casts.id as cast_id,
      1 as casted,
      0 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts
    FROM casts, max_cast_action
    WHERE casts.timestamp 
        BETWEEN max_cast_action.max_ts 
        AND max_cast_action.max_ts + interval '1 days'
    UNION ALL
    SELECT
      casts.fid as fid,
      pcast.id as cast_id,
      0 as casted,
      1 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as action_ts
    FROM casts CROSS JOIN max_cast_action
    INNER JOIN casts as pcast ON (pcast.hash = casts.parent_hash)
    WHERE 
      casts.timestamp 
        BETWEEN max_cast_action.max_ts 
          AND max_cast_action.max_ts + interval '1 days'
    UNION ALL
    SELECT 
      reactions.fid as fid,
      casts.id as cast_id,
      0 as casted,
      0 as replied,
      CASE reactions.type WHEN 2 THEN 1 ELSE 0 END as recasted,
      CASE reactions.type WHEN 1 THEN 1 ELSE 0 END as liked,
      reactions.timestamp as action_ts
    FROM reactions CROSS JOIN max_cast_action
    INNER JOIN casts ON (casts.hash = reactions.target_cast_hash)
    WHERE 
      reactions.timestamp 
        BETWEEN max_cast_action.max_ts 
          AND max_cast_action.max_ts + interval '1 days'
    ORDER BY action_ts ASC
    LIMIT {limit}
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {insert_sql}")
      cursor.execute(insert_sql)


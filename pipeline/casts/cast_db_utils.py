import logging

from timer import Timer

import psycopg2
import psycopg2.extras


@Timer(name="insert_cast_interaction")
def insert_cast_interaction(logger: logging.Logger, pg_dsn: str, limit: int):
  insert_sql = f"""
    INSERT INTO k3l_cast_interaction
    WITH max_cast_interaction AS (
      SELECT 
        coalesce(max(interaction_ts),now() - interval '90 days')  as max_ts
      FROM k3l_cast_interaction
    )
    SELECT
      casts.fid as fid,
      casts.hash as cast_hash,
      1 as casted,
      0 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as interaction_ts
    FROM casts, max_cast_interaction
    WHERE casts.timestamp 
        BETWEEN max_cast_interaction.max_ts 
        AND max_cast_interaction.max_ts + interval '1 days'
    UNION ALL
    SELECT
      casts.fid as fid,
      casts.parent_hash as cast_hash,
      0 as casted,
      1 as replied,
      0 as recasted,
      0 as liked,
      casts.timestamp as interaction_ts
    FROM casts, max_cast_interaction
    WHERE 
      casts.parent_hash is not null
      AND
      casts.timestamp 
        BETWEEN max_cast_interaction.max_ts 
          AND max_cast_interaction.max_ts + interval '1 days'
    UNION ALL
    SELECT 
      reactions.fid as fid,
      reactions.target_cast_hash as cast_hash,
      0 as casted,
      0 as replied,
      CASE reactions.type WHEN 2 THEN 1 ELSE 0 END as recasted,
      CASE reactions.type WHEN 1 THEN 1 ELSE 0 END as liked,
      reactions.timestamp as interaction_ts
    FROM reactions, max_cast_interaction
    WHERE 
      reactions.target_cast_hash is not null
      AND
      reactions.timestamp 
        BETWEEN max_cast_interaction.max_ts 
          AND max_cast_interaction.max_ts + interval '1 days'
    ORDER BY interaction_ts ASC
    LIMIT {limit}
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {insert_sql}")
      cursor.execute(insert_sql)


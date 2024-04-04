import logging

from timer import Timer
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from . import channel_model

@Timer(name="upsert_channels")
def upsert_channels(logger: logging.Logger, pg_dsn: str, channels: list[channel_model.Channel]):
  for c in channels:
    dt = datetime.fromtimestamp(c.created_at_ts)

    fetch_sql = f"""
      INSERT INTO k3l_channels(id, project_url, name, description, image_url, lead_fid, host_fids, created_at_ts, follower_count, processed_ts)
      VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
      ON CONFLICT(id)
      DO UPDATE SET
        id = EXCLUDED.id,
        project_url = EXCLUDED.project_url,
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        image_url = EXCLUDED.image_url,
        lead_fid = EXCLUDED.lead_fid,
        host_fids = EXCLUDED.host_fids,
        created_at_ts = EXCLUDED.created_at_ts,
        follower_count = EXCLUDED.follower_count,
        processed_ts = EXCLUDED.processed_ts
    """
    with psycopg2.connect(pg_dsn) as conn:
      with conn.cursor() as cursor:
        logger.info(f"Executing: {fetch_sql}")
        cursor.execute(fetch_sql, (c.id, c.project_url, c.name, c.description, c.image_url, c.lead_fid, c.host_fids, dt, c.follower_count, datetime.now()))

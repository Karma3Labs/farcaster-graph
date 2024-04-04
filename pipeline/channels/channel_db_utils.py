import logging

from timer import Timer
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from . import channel_model

# @Timer(name="upsert_channels")
# def insert_channel_follows_json(logger: logging.Logger, pg_dsn: str, channel_id: str, fids: list[int]):
#   fid_tuple = [ '{' + f'''"channel_id":"{channel_id}","follower_fid":{f},"processed_ts":"{datetime.now()}"''' + '}' for f in fids]
#   fid_tuple_str = "[" + ",".join(fid_tuple) + "]"
#   print(fid_tuple_str)
#   dt = datetime.now()
#   # TODO (SJ): use json to insert in bulk
#   fetch_sql = f"""
#     INSERT INTO k3l_channel_followers(channel_id, follower_fid, processed_ts)
#     select channel_id::text,
#         follower_fid::text,
#         processed_ts::datetime from json_populate_recordset(null::k3l_channel_followers, to_json(%s)) as (
#         channel_id text,
#         follower_fid text,
#         processed_ts datetime
#     )
#   """

#   with psycopg2.connect(pg_dsn) as conn:
#     with conn.cursor() as cursor:
#       logger.info(f"Executing: {fetch_sql}")
#       cursor.execute(fetch_sql, (fid_tuple_str,))

@Timer(name="insert_channel_follows")
def insert_channel_follows(logger: logging.Logger, pg_dsn: str, channel_id: str, fids: list[int]):
  # fid_tuple = [(channel_id, f) for f in fids]
  for fid in fids:
    dt = datetime.now()
    # TODO (SJ): use json to insert in bulk
    fetch_sql = f"""
      INSERT INTO k3l_channel_followers(channel_id, follower_fid, processed_ts)
      VALUES(%s, %s, %s)
    """

    with psycopg2.connect(pg_dsn) as conn:
      with conn.cursor() as cursor:
        logger.info(f"Executing: {fetch_sql}")
        cursor.execute(fetch_sql, (channel_id, fid, datetime.now()))

@Timer(name="upsert_channels")
def upsert_channels(logger: logging.Logger, pg_dsn: str, channels: list[channel_model.Channel]):
  for c in channels:
    dt = datetime.fromtimestamp(c.created_at_ts)
    # TODO (SJ): use json to insert in bulk
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


# @Timer(name="upsert_channels_json")
# def upsert_channels_json(logger: logging.Logger, pg_dsn: str, channels: list[any]):
#   chans = []
#   for c in channels:
#     chans.append(str(c))

#   chans_json = "[" + ",".join(chans) + "]"
#   # for c in channels:
#   #   dt = datetime.fromtimestamp(c.created_at_ts)

#   #   # TODO (SJ): use json to insert in bulk
#   print(chans_json)
#   fetch_sql = f"""
#     INSERT INTO k3l_channels(id, project_url, name, description, image_url, lead_fid, host_fids, created_at_ts, follower_count, processed_ts)
#     select * from json_populate_recordset(null::k3l_channels, to_json(%s)) as (
#         id text,
#         project_url text,
#         name text,
#         description text,
#         image_url text,
#         lead_fid bigint,
#         host_fids bigint[],
#         created_at_ts datetime,
#         follower_count bigint,
#         processed_ts datetime
#     )
#     ON CONFLICT(id)
#     DO UPDATE SET
#       id = EXCLUDED.id,
#       project_url = EXCLUDED.project_url,
#       name = EXCLUDED.name,
#       description = EXCLUDED.description,
#       image_url = EXCLUDED.image_url,
#       lead_fid = EXCLUDED.lead_fid,
#       host_fids = EXCLUDED.host_fids,
#       created_at_ts = EXCLUDED.created_at_ts,
#       follower_count = EXCLUDED.follower_count,
#       processed_ts = EXCLUDED.processed_ts
#   """
#   with psycopg2.connect(pg_dsn) as conn:
#     with conn.cursor() as cursor:
#       logger.info(f"Executing: {fetch_sql}")
#       cursor.execute(fetch_sql, (chans_json,))

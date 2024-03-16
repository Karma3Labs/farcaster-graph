import logging

from timer import Timer

import psycopg2
import psycopg2.extras


@Timer(name="fetch_unprocessed_urls")
def fetch_unprocessed_urls(logger: logging.Logger, pg_dsn: str, limit: int) -> list[tuple]:
  """return will be of the form [(url_id, url)]"""
  fetch_sql = f"""
    SELECT url_id, url
    FROM k3l_url_labels 
    WHERE processed_ts IS NULL
    ORDER BY earliest_cast_dt ASC
    LIMIT {limit}
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {fetch_sql}")
      cursor.execute(fetch_sql)
      url_records = cursor.fetchall()
      return url_records

@Timer(name="update_urls")
def update_urls(logger: logging.Logger, pg_dsn: str, url_categories: list[tuple]):
  """url_categories should be of the form [(url_id, category)]"""
  update_sql = f"""
    UPDATE k3l_url_labels as k
    SET processed_ts=now(), category=v.cat
    FROM (VALUES %s) AS v(id, cat)
    WHERE url_id=v.id;
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
      logger.info(f"Executing: {update_sql}")
      psycopg2.extras.execute_values(cursor,
                                     update_sql, 
                                     url_categories,
                                     template=None, 
                                     page_size=100)


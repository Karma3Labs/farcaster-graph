import logging

import psycopg2
import psycopg2.extras

from timer import Timer


@Timer(name="fetch_unprocessed_urls")
def fetch_unprocessed_urls(
    logger: logging.Logger, pg_dsn: str, limit: int
) -> list[tuple]:
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


@Timer(name="update_url_categories")
def update_url_categories(
    logger: logging.Logger, pg_dsn: str, url_categories: list[tuple]
):
    """url_categories should be of the form [(url_id, category)]"""
    update_sql = """
    UPDATE k3l_url_labels as k
    SET processed_ts=now(), category=v.cat
    FROM (VALUES %s) AS v(id, cat)
    WHERE url_id=v.id;
  """
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {update_sql}")
            psycopg2.extras.execute_values(
                cursor, update_sql, url_categories, template=None, page_size=100
            )


@Timer(name="fetch_unparsed_urls")
def fetch_unparsed_urls(logger: logging.Logger, pg_dsn: str, limit: int) -> list[tuple]:
    """return will be of the form [(url_id, url)]"""
    fetch_sql = f"""
    SELECT url_id, url
    FROM k3l_url_labels 
    WHERE parsed_ts IS NULL
    ORDER BY earliest_cast_dt ASC
    LIMIT {limit}
  """
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {fetch_sql}")
            cursor.execute(fetch_sql)
            url_records = cursor.fetchall()
            return url_records


@Timer(name="update_url_parts")
def update_url_parts(logger: logging.Logger, pg_dsn: str, url_parts: list[tuple]):
    """url_parts should be of the form [(url_id, scheme, domain, subdomain, tld, path)]"""
    update_sql = f"""
    UPDATE k3l_url_labels as k
    SET parsed_ts=now(), scheme=v.scheme, domain=v.domain, subdomain=v.subdomain, tld=v.tld, path=v.path
    FROM (VALUES %s) AS v(id, scheme, domain, subdomain, tld, path)
    WHERE url_id=v.id;
  """
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {update_sql}")
            psycopg2.extras.execute_values(
                cursor, update_sql, url_parts, template=None, page_size=100
            )

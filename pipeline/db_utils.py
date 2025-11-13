import csv
import re
import tempfile
from collections.abc import Iterable
from datetime import datetime
from io import StringIO
from typing import Any

import pandas as pd
import psycopg2
from loguru import logger
from sqlalchemy import create_engine
from supabase import create_client

import utils
from config import settings
from timer import Timer


class SQL:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __str__(self):
        return self.value


def construct_query(query: SQL, where_clause: str) -> SQL:
    if not where_clause:
        condition = ""
    else:
        if "WHERE" in query.value.upper():
            condition = f"AND {where_clause}"
        else:
            condition = f"WHERE {where_clause}"

    query.value = query.value.format(condition=condition)
    return query


def construct_pretrust_query(query: SQL, strategy_id: int) -> SQL:
    query.value = query.value.format(strategy=strategy_id)
    return query


def execute_query(pg_dsn: str, query: str):
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {query}")
            cursor.execute(query)


def ijv_df_read_sql_tmpfile(pg_dsn: str, query: SQL, **query_kwargs) -> pd.DataFrame:
    with Timer(name=query.name):
        sql_query = query.value.format(**query_kwargs)
        with tempfile.TemporaryFile() as tmpfile:
            if settings.IS_TEST:
                copy_sql = f"COPY ({sql_query} LIMIT 100) TO STDOUT WITH CSV HEADER"
            else:
                copy_sql = f"COPY ({sql_query}) TO STDOUT WITH CSV HEADER"
            logger.debug(f"{copy_sql}")
            with psycopg2.connect(pg_dsn) as conn:
                with conn.cursor() as cursor:
                    cursor.copy_expert(copy_sql, tmpfile)
                    tmpfile.seek(0)
                    # types = defaultdict(np.uint64, i='Int32', j='Int32')
                    df = pd.read_csv(tmpfile, dtype={"i": "Int32", "j": "Int32"})
                    return df


def create_temp_table(pg_dsn: str, temp_tbl: str, orig_tbl: str):
    create_sql = f"DROP TABLE IF EXISTS {temp_tbl}; CREATE UNLOGGED TABLE {temp_tbl} AS SELECT * FROM {orig_tbl} LIMIT 0;"
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {create_sql}")
            cursor.execute(create_sql)


def update_date_strategyid(
    pg_dsn: str, temp_tbl: str, strategy_id: int, date_str: str = None
):
    # TODO remove this function as it is no longer used
    date_setting = "date=now()" if date_str is None else f"date='{date_str}'::date"
    update_sql = f"""
    UPDATE {temp_tbl}
    SET {date_setting}, strategy_id={strategy_id}
    WHERE date is null and strategy_id is null
  """
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {update_sql}")
            cursor.execute(update_sql)


def df_insert_not_exists(
    pg_dsn: str,
    df: pd.DataFrame,
    dest_tablename: str,
    constraint: str,
):
    # WARNING - this code does not account for
    # .... single quotes or double quotes in dataframe column values
    query = f"""
        INSERT INTO {dest_tablename}({",".join(df.columns)}) VALUES
        {",".join([str(i) for i in list(df.to_records(index=False))])}
        ON CONFLICT ON CONSTRAINT {constraint} DO NOTHING
    """
    logger.info(f"Inserting {len(df)} rows into table {dest_tablename}")
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.rowcount
            logger.info(f"Inserted {rows} rows into table {dest_tablename}")


def df_insert_copy(pg_url: str, df: pd.DataFrame, dest_tablename: str):
    logger.info(f"Inserting {len(df)} rows into table {dest_tablename}")
    sql_engine = create_engine(pg_url)
    df.to_sql(
        name=dest_tablename,
        con=sql_engine,
        if_exists="append",
        index=False,
        method=_psql_insert_copy,
    )


def _psql_insert_copy(table, conn, keys, data_iter):
    """
    Execute SQL statement inserting data

    Parameters
    ----------
    table : pandas.io.sql.SQLTable
    conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
    keys : list of str
        Column names
    data_iter : Iterable that iterates the values to be inserted
    """
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ", ".join('"{}"'.format(k) for k in keys)
        if table.schema:
            table_name = "{}.{}".format(table.schema, table.name)
        else:
            table_name = table.name

        sql = "COPY {} ({}) FROM STDIN WITH CSV".format(table_name, columns)
        cur.copy_expert(sql=sql, file=s_buf)


# DEPRECATED
@Timer(name="fetch_channel_details")
def fetch_channel_details(pg_url: str, channel_id: str):
    # TODO move this to channels/channel_db_utils
    engine = create_engine(pg_url)
    try:
        with engine.connect() as conn:
            tmp_sql = f"select * from warpcast_channels_data where id = '{channel_id}'"
            df = pd.read_sql_query(tmp_sql, conn)
            if len(df) == 0:
                return None
            return df.to_dict(orient="records")[0]
    except Exception as e:
        logger.error(f"Failed to fetch_channel_details: {e}")
        raise e
    finally:
        engine.dispose()


# DEPRECATED
@Timer(name="fetch_all_channel_details")
def fetch_all_channel_details(pg_url: str):
    # TODO move this to channels/channel_db_utils
    sql_engine = create_engine(pg_url)
    try:
        with sql_engine.connect() as conn:
            tmp_sql = "select * from warpcast_channels_data"
            df = pd.read_sql_query(tmp_sql, conn)
            return df
    except Exception as e:
        logger.error(f"Failed to fetch_all_channel_details: {e}")
        raise e
    finally:
        sql_engine.dispose()


@Timer(name="fetch_channels_for_category")
def fetch_channels_for_category(pg_url: str, category: str):
    # TODO move this to channels/channel_db_utils
    tmp_sql = f"select * from k3l_channel_categories where category='{category}'"
    sql_engine = create_engine(pg_url)
    try:
        with sql_engine.connect() as conn:
            logger.info(f"Executing: {tmp_sql}")
            df = pd.read_sql_query(tmp_sql, conn)
            logger.info(utils.df_info_to_string(df, with_sample=True))
            return df
    except Exception as e:
        logger.error(f"Failed to fetch k3l_channel_categories: {e}")
        raise e
    finally:
        sql_engine.dispose()


def get_supabase_client():
    """Get initialized Supabase client with service role key."""
    return create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
    )


def get_supabase_psycopg2_client(**kwargs) -> psycopg2.extensions.connection:
    """Get Supabase sync (psycopg2) client."""
    return psycopg2.connect(
        host=settings.SUPABASE_DB_HOST,
        port=settings.SUPABASE_DB_PORT,
        user=settings.SUPABASE_DB_USER,
        password=settings.SUPABASE_DB_PASSWORD.get_secret_value(),
        dbname=settings.SUPABASE_DB_NAME,
        **kwargs,
    )


def fetch_cura_users(
    *,
    start_time: datetime | None = None,
    end_time: datetime = None,
    events: Iterable[str] | None = None,
) -> Iterable[int]:
    """
    Fetch Cura users from the ``analytics_events`` table.

    :param start_time: Earliest usage timestamp to include (default: unbounded).
    :param end_time: Latest usage timestamp to include (default: unbounded).
    :param events: List of event names to include (default: all events).
    :return: Generator of Cura user FIDs.
    """
    query = f"""
        SELECT DISTINCT fid
        FROM analytics_events
        WHERE fid IS NOT NULL
            {"AND created_at >= %(start_time)s" if start_time is not None else ""}
            {"AND created_at < %(end_time)s" if end_time is not None else ""}
            {"AND event IN %(events)s" if events is not None else ""}
    """

    with get_supabase_psycopg2_client() as conn, conn.cursor() as cur:
        cur.execute(
            query, dict(start_time=start_time, end_time=end_time, events=tuple(events))
        )
        while rows := cur.fetchmany(100):
            for (fid,) in rows:
                yield fid


def pyformat2format(sql: str, *poargs: Any, **kwargs: Any) -> tuple[str, list[Any]]:
    """
    Formats a SQL query string containing Python-style parameter placeholders into an
    equivalent SQL string with SQL-standard placeholders and a list of corresponding
    parameter values.

    :param sql: SQL query string with Python-style (%s) placeholders.
    :param poargs: Positional arguments for parameters referenced in the SQL string.
    :param kwargs: Keyword arguments for named parameters referenced in the SQL string.
    :return: A tuple containing the reformatted SQL string with SQL-standard placeholders
        and the corresponding list of parameter values.

    >>> pyformat2format("SELECT %(name)s + %s", 3, name=5)
    ('SELECT %s + %s', [5, 3])

    Interpolate keyword parameters as many times as necessary:

    >>> pyformat2format("SELECT %(name)s * %(name)s + %s", 3, name=5)
    ('SELECT %s * %s + %s', [5, 5, 3])

    Raise `ValueError` if required arguments are not provided:

    >>> pyformat2format("SELECT %(name)s + %s + %s", 3, name=5)
    Traceback (most recent call last):
        ...
    ValueError: not enough positional arguments
    >>> pyformat2format("SELECT %(name)s + %(more)s + %(extra)s + %s", 3, name=5)
    Traceback (most recent call last):
        ...
    ValueError: missing keyword argument: 'more'

    Ignore extra positional/keyword arguments:

    >>> pyformat2format("SELECT %(name)s + %s", 3, 4, name=5)
    ('SELECT %s + %s', [5, 3])
    >>> pyformat2format("SELECT %(name)s + %s", 3, name=5, extra=4)
    ('SELECT %s + %s', [5, 3])

    Keep doubled (escaped) percent signs verbatim:

    >>> pyformat2format("SELECT 'needle' LIKE '%%haystack%%'")
    ("SELECT 'needle' LIKE '%%haystack%%'", [])

    Recognize only valid percent sequences (``%s``, ``%(name)s``, and ``%%``):

    >>> pyformat2format("SELECT 'needle' LIKE '%haystack%'")
    Traceback (most recent call last):
        ...
    ValueError: invalid % sequence '%h' in SQL at index 22
    """
    pct_re = re.compile(
        r"%(?:(?P<param>(?:\((?P<name>[A-Za-z_][A-Za-z0-9_]*)\))?s)|(?P<passthrough>%)|(?P<unknown>.))"
    )
    new_sql = ""
    new_args = []
    pos = 0
    for m in pct_re.finditer(sql):
        new_sql += sql[pos : m.start()]
        pos = m.end()
        if m.group("param") is not None:
            name = m.group("name")
            if name is None:
                try:
                    arg, poargs = poargs[0], poargs[1:]
                except IndexError:
                    raise ValueError("not enough positional arguments") from None
            else:
                try:
                    arg = kwargs[name]
                except KeyError:
                    raise ValueError(f"missing keyword argument: {name!r}") from None
            new_sql += "%s"
            new_args.append(arg)
        elif m.group("passthrough") is not None:
            new_sql += m.group()
        elif (unknown := m.group("unknown")) is not None:
            msg = f"invalid % sequence '%h' in SQL at index {m.start()}"
            raise ValueError(msg)
    new_sql += sql[pos:]
    return new_sql, new_args

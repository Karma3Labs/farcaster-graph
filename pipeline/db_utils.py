import tempfile
from io import StringIO
import csv
from enum import Enum

from timer import Timer
from config import settings
from loguru import logger

import psycopg2
import pandas as pd
from sqlalchemy import create_engine

class SQL(Enum): pass

@classmethod
def construct_query(cls, query_template: str, where_clause: str):
    if 'WHERE' in query_template.upper():
        condition = f"AND {where_clause}"
    else:
        condition = f"WHERE {where_clause}"
    return query_template.format(condition=condition)

def execute_query(pg_dsn: str, query: str):
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {query}")
            cursor.execute(query)

def fetch_channel_participants(pg_dsn: str, channel_url: str) -> list[int]:
    query_sql = f"""
    SELECT
      DISTINCT(fid)
    FROM casts
    WHERE root_parent_url = '{channel_url}'
  """
    if settings.IS_TEST:
        query_sql = f"{query_sql} LIMIT 10"
    logger.debug(f"{query_sql}")
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query_sql)
            records = cursor.fetchall()
            fids = [row[0] for row in records]
            return fids

def ijv_df_read_sql_tmpfile(pg_dsn: str, query: SQL, channel_url: str = None) -> pd.DataFrame:
    with Timer(name=query.name):
        with tempfile.TemporaryFile() as tmpfile:
            sql_query = query.value.format(channel_url=channel_url) if channel_url else query.value
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
                    df = pd.read_csv(tmpfile, dtype={'i': 'Int32', 'j': 'Int32'})
                    return df

def create_temp_table(pg_dsn: str, temp_tbl: str, orig_tbl: str):
    create_sql = f"DROP TABLE IF EXISTS {temp_tbl}; CREATE UNLOGGED TABLE {temp_tbl} AS SELECT * FROM {orig_tbl} LIMIT 0;"
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {create_sql}")
            cursor.execute(create_sql)

def update_date_strategyid(pg_dsn: str, temp_tbl: str, strategy_id: int):
    update_sql = f"""
    UPDATE {temp_tbl}
    SET date=now(), strategy_id={strategy_id}
    WHERE date is null and strategy_id is null
  """
    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {update_sql}")
            cursor.execute(update_sql)

def df_insert_copy(pg_url: str, df: pd.DataFrame, dest_tablename: str):
    logger.info(f"Inserting {len(df)} rows into table {dest_tablename}")
    sql_engine = create_engine(pg_url)
    df.to_sql(
        name=dest_tablename,
        con=sql_engine,
        if_exists="append",
        index=False,
        method=_psql_insert_copy
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

        columns = ', '.join('"{}"'.format(k) for k in keys)
        if table.schema:
            table_name = '{}.{}'.format(table.schema, table.name)
        else:
            table_name = table.name

        sql = 'COPY {} ({}) FROM STDIN WITH CSV'.format(table_name, columns)
        cur.copy_expert(sql=sql, file=s_buf)

import tempfile
import logging
from io import StringIO
import csv

from timer import Timer
from .queries import SQL

import psycopg2
import pandas as pd
from sqlalchemy import create_engine


def ijv_df_read_sql_tmpfile(logger: logging.Logger, pg_dsn: str, query: SQL) -> pd.DataFrame:
  with Timer(name=query.name):
    with tempfile.TemporaryFile() as tmpfile:
      copy_sql = f"COPY ({query.value}) TO STDOUT WITH CSV HEADER"
      logger.debug(f"{copy_sql}")
      with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
          cursor.copy_expert(copy_sql, tmpfile)
          tmpfile.seek(0)
          # types = defaultdict(np.uint64, i='Int32', j='Int32')
          df = pd.read_csv(tmpfile, dtype={'i':'Int32', 'j': 'Int32'})
          return df
        
def create_temp_table(logger: logging.Logger, pg_dsn: str, temp_tbl: str, orig_tbl: str ):
  create_sql = f"CREATE UNLOGGED TABLE {temp_tbl} AS SELECT * FROM {orig_tbl} LIMIT 0;"
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
        logger.info(f"Executing: {create_sql}")
        cursor.execute(create_sql)  

def update_date_strategyid(logger: logging.Logger, pg_dsn: str, temp_tbl: str, strategy_id: int):
  update_sql = f"""
    UPDATE {temp_tbl} 
    SET date=now(), strategy_id={strategy_id} 
    WHERE date is null and strategy_id is null
  """
  with psycopg2.connect(pg_dsn) as conn:
    with conn.cursor() as cursor:
        logger.info(f"Executing: {update_sql}")
        cursor.execute(update_sql)  

def df_insert_copy(logger: logging.Logger, pg_url: str, df: pd.DataFrame, dest_tablename: str):
  logger.info(f"Inserting {len(df)} rows into table {dest_tablename}")
  sql_engine = create_engine(pg_url)
  df.to_sql(
      name=dest_tablename,
      con=sql_engine,
      if_exists="append",
      index=False,
      method=_psql_insert_copy
  )

def _psql_insert_copy(table, conn, keys, data_iter): #mehod
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

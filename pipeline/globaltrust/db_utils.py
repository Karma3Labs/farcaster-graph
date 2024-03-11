import tempfile
import logging
import datetime
from io import StringIO
import csv

import utils
from timer import Timer
from .queries import SQL

import psycopg2
import pandas as pd
from sqlalchemy import create_engine


def ijv_df_read_sql_tmpfile(logger: logging.Logger, pg_dsn: str, query: SQL) -> pd.DataFrame:
  with Timer(name=query.name):
    with tempfile.TemporaryFile() as tmpfile:
      copy_sql = f"COPY ({query.value}) TO STDOUT WITH CSV HEADER"
      with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cursor:
          cursor.copy_expert(copy_sql, tmpfile)
          tmpfile.seek(0)
          # types = defaultdict(np.uint64, i='Int32', j='Int32')
          df = pd.read_csv(tmpfile, dtype={'i':'Int32', 'j': 'Int32'})
          logger.info(utils.df_info_to_string(df, with_sample=True))
          return df
        
# def create_temp_localtrust(logger: logging.Logger, pg_dsn: str) -> str:
#   tmp_table_name = "temp_localtrust_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#   lt_temp_create_sql = f"CREATE TABLE {tmp_table_name} AS SELECT * FROM localtrust LIMIT 0;"
#   with psycopg2.connect(pg_dsn) as conn:
#     with conn.cursor() as cursor:
#         cursor.execute(lt_temp_create_sql)

# def df_insert_copy(df: pd.DataFrame, dest_tablename: str, pg_url: str):
#   sql_engine = create_engine(pg_url)
#   df.to_sql(
#       name=dest_tablename,
#       con=sql_engine,
#       if_exists="append",
#       index=False,
#       method=_psql_insert_copy
#   )

# def _psql_insert_copy(table, conn, keys, data_iter): #mehod
#   """
#   Execute SQL statement inserting data

#   Parameters
#   ----------
#   table : pandas.io.sql.SQLTable
#   conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
#   keys : list of str
#       Column names
#   data_iter : Iterable that iterates the values to be inserted
#   """
  
#   dbapi_conn = conn.connection
#   with dbapi_conn.cursor() as cur:
#     s_buf = StringIO()
#     writer = csv.writer(s_buf)
#     writer.writerows(data_iter)
#     s_buf.seek(0)

#     columns = ', '.join('"{}"'.format(k) for k in keys)
#     if table.schema:
#       table_name = '{}.{}'.format(table.schema, table.name)
#     else:
#       table_name = table.name

#     sql = 'COPY {} ({}) FROM STDIN WITH CSV'.format(table_name, columns)
#     cur.copy_expert(sql=sql, file=s_buf)

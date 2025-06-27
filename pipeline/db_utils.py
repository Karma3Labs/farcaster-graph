import csv
import tempfile
from io import StringIO

import pandas as pd
import psycopg2
from loguru import logger
from sqlalchemy import create_engine

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
        INSERT INTO {dest_tablename}({','.join(df.columns)}) VALUES 
        {','.join([str(i) for i in list(df.to_records(index=False))])} 
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


@Timer(name="fetch_channel_domains_for_category")
def fetch_channel_domains_for_category(pg_url: str, category: str):
    # TODO move this to channels/channel_db_utils
    tmp_sql = f"select * from k3l_channel_domains where category='{category}'"
    sql_engine = create_engine(pg_url)
    try:
        with sql_engine.connect() as conn:
            logger.info(f"Executing: {tmp_sql}")
            df = pd.read_sql_query(tmp_sql, conn)
            logger.info(utils.df_info_to_string(df, with_sample=True))
            return df
    except Exception as e:
        logger.error(f"Failed to fetch_all_channel_domains: {e}")
        raise e
    finally:
        sql_engine.dispose()

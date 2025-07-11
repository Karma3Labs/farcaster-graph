from datetime import timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import SQLCheckOperator

default_args = {
    "owner": "karma3labs",
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

_CONN_ID = "eig2_readonly_user"
CHECK_QUERY = """
    WITH 
    channel_rank_stats AS (
        SELECT 
            COUNT(*) AS tot_rows, 
            COUNT(DISTINCT channel_id) AS tot_channels,
            strategy_name
        FROM k3l_channel_rank
        GROUP BY strategy_name
    ),
    channel_fids_stats as (
        SELECT 
            COUNT(*) AS tot_rows, 
            COUNT(DISTINCT channel_id) AS tot_channels,
            strategy_name
        -- TODO change table name to k3l_channel_fids
        FROM k3l_channel_rank
        GROUP BY strategy_name
    )
    SELECT 
        BOOL_AND(
                t2.tot_rows >= t1.tot_rows 
                AND t2.tot_channels >= t1.tot_channels
                AND t2.strategy_name IS NOT NULL
                )
    FROM channel_rank_stats as t1
    LEFT JOIN channel_fids_stats as t2 ON (t2.strategy_name = t1.strategy_name)
"""

with DAG(
    "one_off_trial_sql",
    default_args=default_args,
    description="One off dag to test new features",
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    start = EmptyOperator(task_id="start")

    sql_check = SQLCheckOperator(task_id="sql_check", sql=CHECK_QUERY, conn_id=_CONN_ID)

    end = EmptyOperator(task_id="end")

    start >> sql_check >> end

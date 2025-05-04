from datetime import timedelta, datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import (
    # SQLCheckOperator,
    # SQLColumnCheckOperator,
    # SQLIntervalCheckOperator,
    # SQLTableCheckOperator,
    SQLThresholdCheckOperator,
    # SQLValueCheckOperator,
    # SQLExecuteQueryOperator,
)

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

_ALT_CONN_ID = "eig8_postgres_user"

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    "monitor_nindexer",
    default_args=default_args,
    description="Monitor the status of replication and \
                raise alerts if there are significant lags",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2024, 8, 1),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    start = EmptyOperator(task_id="start")

    lag_casts_at = SQLThresholdCheckOperator(
        task_id="lag_casts_at",
        conn_id=_ALT_CONN_ID,
        sql="""
        SELECT 
	        EXTRACT(EPOCH FROM (now() - max(created_at))) as max_createdat_lag_ms
        FROM neynarv2.casts
        WHERE timestamp > now() - interval '1 days'
        AND timestamp <= now() -- ignore casts with bad timestamp in the future
        """,
        min_threshold=0,
        max_threshold=600, # fail task if more than 10 minutes of lag
    )

    lag_casts_ts = SQLThresholdCheckOperator(
        task_id="lag_casts_ts",
        conn_id=_ALT_CONN_ID,
        sql="""
        SELECT 
	        EXTRACT(EPOCH FROM (now() - max(timestamp))) as max_ts_lag_ms
        FROM neynarv2.casts
        WHERE timestamp > now() - interval '1 days'
        AND timestamp <= now() -- ignore casts with bad timestamp in the future
        """,
        min_threshold=0,
        max_threshold=600, # fail task if more than 10 minutes of lag
    )

    # lag_reactions_ts = SQLThresholdCheckOperator(
    #     task_id="lag_reactions_ts",
    #     conn_id=_ALT_CONN_ID,
    #     sql="""
    #     SELECT
	#         EXTRACT(EPOCH FROM (now() - max(timestamp))) as max_ts_lag_ms
    #     FROM neynarv2.reactions
    #     WHERE timestamp > now() - interval '1 days'
    #     AND timestamp <= now() -- ignore casts with bad timestamp in the future
    #     """,
    #     min_threshold=0,
    #     max_threshold=600, # fail task if more than 10 minutes of lag
    # )

    lag_reactions_ts = EmptyOperator(task_id="lag_reactions_ts")

    end = EmptyOperator(task_id="end")

    start >> lag_casts_at >> lag_casts_ts >> lag_reactions_ts >> end
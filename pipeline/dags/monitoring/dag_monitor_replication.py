from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import (  # SQLCheckOperator,; SQLColumnCheckOperator,; SQLIntervalCheckOperator,; SQLValueCheckOperator,; SQLExecuteQueryOperator,
    SQLTableCheckOperator,
    SQLThresholdCheckOperator,
)
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

_CONN_ID = "eig2_postgres_user"
_ALT_CONN_ID = "eig8_postgres_user"

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    "monitor_replication",
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

    check_wal_status = SQLTableCheckOperator(
        task_id="check_wal_status",
        conn_id=_CONN_ID,
        table="pg_replication_slots",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) = 2",
                "partition_clause": "wal_status='reserved'",
            }
        },
    )

    check_wal_status8 = SQLTableCheckOperator(
        task_id="check_wal_status8",
        conn_id=_ALT_CONN_ID,
        table="pg_replication_slots",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) = 2",
                "partition_clause": "wal_status='reserved'",
            }
        },
    )

    check_replication_state = SQLTableCheckOperator(
        task_id="check_replication_state",
        conn_id=_CONN_ID,
        table="pg_stat_replication",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) = 2",
                "partition_clause": "state='streaming'",
            }
        },
    )

    check_replication_state8 = SQLTableCheckOperator(
        task_id="check_replication_state8",
        conn_id=_ALT_CONN_ID,
        table="pg_stat_replication",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) = 2",
                "partition_clause": "state='streaming'",
            }
        },
    )

    lag_check = SQLThresholdCheckOperator(
        task_id="lag_check",
        conn_id=_CONN_ID,
        sql="SELECT round(EXTRACT(epoch FROM max(replay_lag))/60) FROM pg_stat_replication",
        min_threshold=0,
        max_threshold=60,  # fail task if more than 60 minutes of lag
    )

    lag_check8 = SQLThresholdCheckOperator(
        task_id="lag_check8",
        conn_id=_ALT_CONN_ID,
        sql="SELECT round(EXTRACT(epoch FROM max(replay_lag))/60) FROM pg_stat_replication",
        min_threshold=0,
        max_threshold=60,  # fail task if more than 60 minutes of lag
    )

    end = EmptyOperator(task_id="end")

    start >> check_wal_status >> check_replication_state >> lag_check >> end
    start >> check_wal_status8 >> check_replication_state8 >> lag_check8 >> end

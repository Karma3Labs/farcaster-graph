from datetime import timedelta, datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import (
    # SQLCheckOperator,
    # SQLColumnCheckOperator,
    # SQLIntervalCheckOperator,
    SQLTableCheckOperator,
    # SQLThresholdCheckOperator,
    # SQLValueCheckOperator,
    # SQLExecuteQueryOperator,
)

# from hooks.discord import send_alert_discord
# from hooks.pagerduty import send_alert_pagerduty

_CONN_ID = "eig2_postgres_user"

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    "monitor_replication",
    default_args=default_args,
    description="Monitor the status of replication and \
                raise alerts if there are significant lags",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2024, 8, 1),
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
                "partition_clause": "wal_status='reserved'"
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
                "partition_clause": "state='streaming'"
            }
        },
    )

    end = EmptyOperator(task_id="end")

    start >> check_wal_status >> check_replication_state >> end

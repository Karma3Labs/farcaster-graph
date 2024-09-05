from datetime import timedelta, datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import (
    # SQLCheckOperator,
    # SQLColumnCheckOperator,
    # SQLIntervalCheckOperator,
    SQLTableCheckOperator,
    SQLThresholdCheckOperator,
    # SQLValueCheckOperator,
    # SQLExecuteQueryOperator,
)

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

_CONN_ID = "sandbox_postgres_user"

default_args = {
    "owner": "karma3labs",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    "monitor_sandbox",
    default_args=default_args,
    description="Monitor the status of sandbox and \
                raise alerts if there are significant lags",
    schedule_interval=timedelta(minutes=10),
    start_date=datetime(2024, 8, 1),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    start = EmptyOperator(task_id="start")

    check_channel_rank = SQLThresholdCheckOperator(
        task_id="check_channel_rank", # covers the channel_fids table also
        conn_id=_CONN_ID,
        sql="SELECT count(*) FROM k3l_channel_rank WHERE compute_ts > now() - interval '12 hours' AND strategy_name = 'channel_engagement'",
        min_threshold=1_900_000
    )

    check_global_engagement_rank = SQLThresholdCheckOperator(
        task_id="check_global_engagement_rank", # covers the globaltrust table also
        conn_id=_CONN_ID,
        sql="SELECT count(*) FROM k3l_rank WHERE date > now() - interval '1 days' AND strategy_name = 'engagement'",
        min_threshold=700_000
    )

    check_parent_casts_count = SQLTableCheckOperator(
        task_id="check_parent_casts_count",
        conn_id=_CONN_ID,
        table="k3l_recent_parent_casts",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) > 100",
                "partition_clause": "timestamp > now() - interval '30 min'"
            }
        },
    )

    check_parent_casts_lag = SQLThresholdCheckOperator(
        task_id="check_parent_casts_lag",
        conn_id=_CONN_ID,
        sql="""SELECT
	            (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - max(timestamp)))/60)::integer as diff_mins
                FROM k3l_recent_parent_casts""",
        min_threshold=0,
        max_threshold=30
    )

    check_cast_actions_count = SQLTableCheckOperator(
        task_id="check_cast_actions_count",
        conn_id=_CONN_ID,
        table="k3l_cast_action",
        checks={
            "row_count_check": {
                "check_statement": "COUNT(*) > 10000",
                "partition_clause": "action_ts > now() - interval '30 min'"
            }
        },
    )

    check_cast_actions_lag = SQLThresholdCheckOperator(
        task_id="check_cast_actions_lag",
        conn_id=_CONN_ID,
        sql="""SELECT
	            (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - max(action_ts)))/60)::integer as diff_mins
                FROM k3l_cast_action""",
        min_threshold=0,
        max_threshold=30
    )

    end = EmptyOperator(task_id="end")

    (
        start
        >> check_channel_rank
        >> check_global_engagement_rank
        >> check_parent_casts_count
        >> check_parent_casts_lag
        >> check_cast_actions_count
        >> check_cast_actions_lag
        >> end
    )

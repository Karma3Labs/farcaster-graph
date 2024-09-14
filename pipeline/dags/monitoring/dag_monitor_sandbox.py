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
        # 26 hours because date timezone transitions
        sql="SELECT count(*) FROM k3l_channel_rank WHERE compute_ts > now() - interval '26 hours' AND strategy_name = 'channel_engagement'",
        min_threshold=1_500_000,
        max_threshold=3_000_000 # alert if size doubles
    )

    check_global_engagement_rank = SQLThresholdCheckOperator(
        task_id="check_global_engagement_rank", # covers the globaltrust table also
        conn_id=_CONN_ID,
        # 26 hours because date timezone transitions
        sql="SELECT count(*) FROM k3l_rank WHERE date >= (now() - interval '26 hours')::date AND strategy_name = 'engagement'",
        min_threshold=700_000,
        max_threshold=1_400_000 # alert if size doubles
    )

    # use SQLThresholdCheckOperator instead of SQLTableCheckOperator
    # when SQLThresholdCheckOperator fails, we get actual count and easier to debug
    check_parent_casts_count = SQLThresholdCheckOperator(
        task_id="check_parent_casts_count",
        conn_id=_CONN_ID,
        sql = "SELECT count(*) FROM k3l_recent_parent_casts WHERE timestamp > now() - interval '30 min'",
        min_threshold=100,
        max_threshold=1_000_000, # some arbitrarily large number
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

    # use SQLThresholdCheckOperator instead of SQLTableCheckOperator
    # when SQLThresholdCheckOperator fails, we get actual count and easier to debug
    check_cast_actions_count = SQLThresholdCheckOperator(
        task_id="check_cast_actions_count",
        conn_id=_CONN_ID,
        sql="SELECT count(*) FROM k3l_cast_action WHERE action_ts > now() - interval '45 min'",
        min_threshold=1_000,
        max_threshold=100_000_000# some arbitrarily large number
    )

    check_cast_actions_lag = SQLThresholdCheckOperator(
        task_id="check_cast_actions_lag",
        conn_id=_CONN_ID,
        sql="""SELECT
	            (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - max(action_ts)))/60)::integer as diff_mins
                FROM k3l_cast_action""",
        min_threshold=0,
        max_threshold=45
    )

    end = EmptyOperator(task_id="end")

    (
        start
        >> check_channel_rank
        >> check_global_engagement_rank
        >> check_parent_casts_lag
        >> check_cast_actions_lag
        >> check_parent_casts_count
        >> check_cast_actions_count
        >> end
    )

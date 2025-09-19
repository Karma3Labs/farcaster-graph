from datetime import datetime, timedelta

import pytz
from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}


def _1amutc_time():
    utc_tz = pytz.timezone("UTC")
    utc_1am_str = " ".join(
        [datetime.now(utc_tz).strftime("%Y-%m-%d"), "01:00:00"]
    )
    utc_time = utc_tz.localize(
        datetime.strptime(utc_1am_str, "%Y-%m-%d %H:%M:%S")
    )
    return utc_time


with DAG(
    dag_id="notify_channel_top_cast",
    default_args=default_args,
    description="daily notifications for top cast in channels",
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval="0 1 * * *",  # every day at 01:00 UTC
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    skip_notify = EmptyOperator(task_id="skip_notify")

    notify = BashOperator(
        task_id="notify",
        bash_command="cd /pipeline && ./run_notify_channel_top_cast.sh -w . -v .venv -r ",
        dag=dag,
    )

    @task.branch(task_id="check_last_successful")
    def check_last_successful(**context) -> bool:
        now = datetime.now(pytz.utc)
        prev_run_date = context["prev_data_interval_end_success"]
        daily_run = _1amutc_time()
        print(f"now: {now}, prev_run_date: {prev_run_date}, daily_run: {daily_run}")
        if now > daily_run and (prev_run_date is None or prev_run_date < daily_run):
            # Last successful run was before today, so we should run
            print(f"Last run {prev_run_date} was before {daily_run}, so we should run")
            return "notify"
        return "skip_notify"

    check_last_successful = check_last_successful()

    check_last_successful >> skip_notify

    check_last_successful >> notify
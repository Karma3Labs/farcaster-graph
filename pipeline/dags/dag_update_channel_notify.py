from datetime import datetime, timedelta, timezone
import pytz

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task

from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

def _monday_9ampacific_in_utc_time():
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_9am_str = ' '.join([datetime.datetime.now(pacific_tz).strftime("%Y-%m-%d"),'09:00:00'])
    pacific_time = pacific_tz.localize(datetime.datetime.strptime(pacific_9am_str, '%Y-%m-%d %H:%M:%S'))
    utc_time = pacific_time.astimezone(pytz.utc)
    monday_utc_time = utc_time - datetime.timedelta(days=utc_time.weekday() - 0) 
    return monday_utc_time

with DAG(
    dag_id='update_channel_notify',
    default_args=default_args,
    description='channel notifications started by trigger dag or manually',
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    skip_notify = EmptyOperator(task_id="skip_notify")

    notify = BashOperator(
            task_id="notify",
            bash_command="cd /pipeline && ./run_update_channel_notify.sh  -w . -v .venv -r -d ",
            dag=dag)
    
    @task.branch(task_id="check_last_successful")
    def check_last_successful(**context) -> bool:
        prev_tokens_date = context['prev_data_interval_start_success']
        if prev_tokens_date < _monday_9ampacific_in_utc_time():
            # Last successful run was before 9am on Monday, so we should run
            print(f"Last run was before {prev_tokens_date}, so we should run")
            return "notify"
        return "skip_notify"

    check_last_successful = check_last_successful()

    check_last_successful  >> skip_notify

    check_last_successful  >> notify


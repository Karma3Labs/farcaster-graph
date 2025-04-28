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

def wed_9ampacific_in_utc_time():
    wednesday_dow = 2
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_9am_str = ' '.join([datetime.now(pacific_tz).strftime("%Y-%m-%d"),'09:00:00'])
    pacific_time = pacific_tz.localize(datetime.strptime(pacific_9am_str, '%Y-%m-%d %H:%M:%S'))
    utc_time = pacific_time.astimezone(pytz.utc) 
    return utc_time - datetime.timedelta(days=utc_time.weekday() - wednesday_dow)

with DAG(
    dag_id='notify_channel_weekly_mods',
    default_args=default_args,
    description='weekly notifications to mods',
    start_date=datetime(2024, 7, 10, 18),
    schedule_interval='30 16 * * 3', # every Wednesday at 16:30/17:30 UTC / 09:30 Pacific 
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    skip_notify = EmptyOperator(task_id="skip_notify")

    notify = BashOperator(
            task_id="notify",
            bash_command=(
                "cd /pipeline && ./run_notify_channel_weekly_mods.sh "
                " -w . -v .venv -b channels/Bot_Fids.csv -d "),
            dag=dag)
    
    @task.branch(task_id="check_last_successful")
    def check_last_successful(**context) -> bool:
        now = datetime.now(pytz.utc)
        prev_run_date = context['prev_data_interval_end_success']
        weekly_run = wed_9ampacific_in_utc_time() 
        print(f"now: {now}, prev_run_date: {prev_run_date}, weekly_run: {weekly_run}")
        if (
            now > weekly_run
            and (prev_run_date is None or prev_run_date < weekly_run)
        ):
            # Last successful run was before today, so we should run
            print(f"Last run {prev_run_date} was before {weekly_run}, so we should run")
            return "notify"
        return "skip_notify"

    check_last_successful = check_last_successful()

    check_last_successful  >> skip_notify

    check_last_successful  >> notify


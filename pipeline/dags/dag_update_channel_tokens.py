from datetime import datetime, timedelta

from airflow import DAG
# from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator


from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='update_channel_tokens',
    default_args=default_args,
    description='update channel tokens started by trigger dag or manually',
    start_date=datetime(2024, 7, 10, 18),
    schedule=None, # this dag is triggered by dag trigger_channel_points_tokens
    # schedule_interval='0 0 * * *', # every day at 00:00 UTC / 16:00 PST 
    # schedule_interval=timedelta(days=1),
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    prepare = BashOperator(
        task_id="prepare",
        bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t prep -s daily -r {{ run_id }}",
        dag=dag)

    distribute = BashOperator(
        task_id="distribute",
        bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t distrib",
        dag=dag)
    
    verify = BashOperator(
        task_id="verify",
        bash_command="cd /pipeline && ./run_update_channel_tokens.sh  -w . -v .venv -t verify",
        dag=dag)

    trigger_update_channel_points = TriggerDagRunOperator(
            task_id="trigger_update_channel_points",
            trigger_dag_id="update_channel_points_v2",
            conf={"trigger": "update_channel_tokens"},
            wait_for_completion=True,
        )

    prepare >> distribute >> verify >> trigger_update_channel_points


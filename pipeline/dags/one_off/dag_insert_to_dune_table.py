from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty


default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}


with DAG(
    dag_id='one_off_insert_to_dune_tables',
    default_args=default_args,
    description='This inserts globaltrust and channel_ranking into dune',
    schedule_interval=None,
    start_date=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    task4 = BashOperator(
        task_id='overwrite_globaltrust_in_dune_v3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh overwrite_globaltrust_in_dune_v3"
    )

    task5 = BashOperator(
        task_id='overwrite_channel_rank_in_dune_v3',
        bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh overwrite_channel_rank_in_dune_v3"
    )

    [task4, task5]


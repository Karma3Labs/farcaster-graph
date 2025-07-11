from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id="refresh_rank_view_v0",
    default_args=default_args,
    description="This refreshes k3l_rank materialized view and vacuums k3l_rank table",
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval='0 1-23/6 * * *',
    schedule=None,
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id="refresh_view_k3l_rank_e8",
        bash_command="""cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
        REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_rank; "
        """,
    )

    task2 = BashOperator(
        task_id="vacuum_k3l_rank_e8",
        bash_command="""cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
        VACUUM ANALYZE k3l_rank; "
        """,
    )

    task1 >> task2

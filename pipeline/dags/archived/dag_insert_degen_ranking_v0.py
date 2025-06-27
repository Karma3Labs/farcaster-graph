from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "coder2j",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id="dag_degen_insert_ranking_v0",
    default_args=default_args,
    description="Process DEGEN tips from casts",
    start_date=datetime(2024, 7, 9, 18),
    # schedule_interval='10 */6 * * *',
    schedule_interval=None,
    catchup=False,
) as dag:

    task_update_degen_tips = BashOperator(
        task_id="update_degen_tips_v0",
        bash_command="""cd /pipeline/ && ./run_create_degen_db_functions.sh -v .venv -t insert_scores
        """,
    )

    task_analyze_degen_tips = BashOperator(
        task_id="analyze_degen_tips_v0",
        bash_command="""cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        ANALYZE k3l_degen_tips;
        ANALYZE k3l_cast_action;"
        """,
    )

    # Set up the task dependencies
    task_update_degen_tips >> task_analyze_degen_tips

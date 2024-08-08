from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'coder2j',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id='dag_degen_tips_processing_v0',
    default_args=default_args,
    description='Process DEGEN tips from casts',
    start_date=datetime(2024, 7, 9, 18),
    schedule_interval='*/20 * * * *',  # Run every 20 minutes
    catchup=False,
) as dag:

    task_create_degen_functions = BashOperator(
        task_id='create_degen_functions_v0',
        bash_command='cd /pipeline/ && ./run_create_degen_functions.sh'
    )

    task_update_degen_tips = BashOperator(
        task_id='update_degen_tips_v0',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        SELECT update_degen_tips();"
        '''
    )

    task_analyze_degen_tips = BashOperator(
        task_id='analyze_degen_tips_v0',
        bash_command='''cd /pipeline/ && ./run_eigen2_postgres_sql.sh -w . "
        ANALYZE k3l_degen_tips;
        ANALYZE k3l_cast_action;
        ANALYZE casts;"
        '''
    )

    # Set up the task dependencies
    task_create_degen_functions >> task_update_degen_tips >> task_analyze_degen_tips
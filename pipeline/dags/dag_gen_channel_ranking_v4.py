from datetime import datetime, timedelta
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLCheckOperator
from airflow.decorators import task, dag, task_group
from airflow.utils.trigger_rule import TriggerRule

import math
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    'owner': 'karma3labs',
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

CONN_ID = "eig8_k3l_user"
N_CHUNKS = 100  # Define the number of chunks

CHECK_QUERY = """
    WITH 
    channel_rank_stats AS (
    SELECT
        COUNT(*) as tot_rows,
        COUNT(DISTINCT channel_id) AS tot_channels,
        strategy_name
    FROM k3l_channel_rank
    GROUP BY strategy_name
    ),
    channel_fids_stats AS (
        SELECT
            COUNT(*) as tot_rows,
            COUNT(DISTINCT channel_id) AS tot_channels,
            strategy_name				
        FROM k3l_channel_fids
    GROUP BY strategy_name
    ),
    threshold_checks AS (
    SELECT
        CASE
            WHEN current.strategy_name = 'channel_engagement'
            THEN BOOL_AND(
                ABS(new.tot_rows - current.tot_rows)::decimal/GREATEST(new.tot_rows, current.tot_rows) * 100 <= 5
                AND new.tot_channels >= current.tot_channels
                AND new.strategy_name IS NOT NULL
                )
            WHEN current.strategy_name = '1d_engagement'
            THEN BOOL_AND(
                ABS(new.tot_rows - current.tot_rows)::decimal/GREATEST(new.tot_rows, current.tot_rows) * 100 <= 50
                AND ABS(new.tot_channels - current.tot_channels)::decimal/GREATEST(new.tot_rows, current.tot_rows) * 100 <= 50
                AND new.strategy_name IS NOT NULL
                )
            ELSE BOOL_AND(
                ABS(new.tot_rows - current.tot_rows)::decimal/GREATEST(new.tot_rows, current.tot_rows) * 100 <= 25
                AND ABS(new.tot_channels - current.tot_channels)::decimal/GREATEST(new.tot_rows, current.tot_rows) * 100 <= 25
                AND new.strategy_name IS NOT NULL
                )
        END as strategy_check
    FROM channel_rank_stats as current
    LEFT JOIN channel_fids_stats as new ON (new.strategy_name = current.strategy_name)
    GROUP BY current.strategy_name, new.strategy_name
    )
    SELECT
        BOOL_AND(strategy_check)
    FROM threshold_checks
"""

@dag(
    dag_id='gen_channel_ranking_v4',
    default_args=default_args,
    description='This runs the channel ranking pipeline',
    start_date=datetime(2024, 10, 1),
    # schedule_interval='0 */6 * * *',
    schedule_interval=None, # triggered by external trigger
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False  # To avoid backfilling if not required
)
def create_dag():

    @task_group(group_id='prep_db')
    def tg_prep_db():

        sanitycheck_before_truncate8 = SQLCheckOperator(
            task_id='sanitycheck_before_truncate8',
            sql=CHECK_QUERY,
            conn_id=CONN_ID
        )
        # sanitycheck_before_truncate8 = EmptyOperator(task_id='sanitycheck_before_truncate8')

        truncate_ch_fids8 = BashOperator(
            task_id='truncate_ch_fids8',
            bash_command='''cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
            BEGIN;
            DROP TABLE IF EXISTS k3l_channel_fids_old;
            CREATE UNLOGGED TABLE k3l_channel_fids_old AS SELECT * FROM k3l_channel_fids;
            TRUNCATE TABLE k3l_channel_fids;
            COMMIT;"
            '''
        )
        # OK to truncate 'k3l_channel_fids' because there are no dependencies
        # .. except for 'k3l_channel_rank' materialized view which 
        # .. does not get refreshed until the very end and only 
        # .. after an additional sanity check
        sanitycheck_before_truncate8 >> truncate_ch_fids8

    @task_group(group_id='compute_group')
    def tg_compute():

        prep_channel_data = BashOperator(
            task_id='prep_channel_data',
            bash_command=(
                "cd /pipeline && ./run_channel_scraper_v4.sh -w . -v .venv"
                " -t prep -r {{ run_id }} -n 60"
                f" -c {N_CHUNKS}"
            ),
        )

        @task
        def extract_batch_ids() -> list:
            return list(range(1,N_CHUNKS+1))

        @task(max_active_tis_per_dagrun=8)
        def process_channel_chunk(batch_id: int, interval: int, run_id):
            bash_command = (
                "cd /pipeline && ./run_channel_scraper_v4.sh -w . -v .venv"
                f" -t process -r {run_id} -n 60"
                " -s channels/Seed_Fids.csv -b channels/Bot_Fids.csv"
                f" -i {batch_id}"
            )
            process_task = BashOperator(
                task_id=f'process_channels_chunk_{batch_id}',
                bash_command=bash_command,
                env={'PYTHONUNBUFFERED': '1'}  # Ensures real-time logging
            )
            process_task.execute({})

        extract_ids = extract_batch_ids()

        # Create dynamic tasks
        process_60d_tasks = process_channel_chunk.partial(interval=60).expand(batch_id=extract_ids)

        prep_channel_data >> extract_ids >> process_60d_tasks 

    @task_group(group_id='refesh_db')
    def tg_db():

        sanitycheck_before_refresh8 = SQLCheckOperator(
            task_id='sanitycheck_before_refresh8',
            sql=CHECK_QUERY,
            conn_id=CONN_ID
        )

        # sanitycheck_before_refresh8 = EmptyOperator(task_id='sanitycheck_before_refresh8')

        refresh_ch_rank8 = BashOperator(
            task_id='refresh_ch_rank8',
            bash_command='''cd /pipeline/ && ./run_eigen8_postgres_sql.sh -w . "
            REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_channel_rank;"
            ''',
            trigger_rule=TriggerRule.ALL_SUCCESS
        )
        # refresh_ch_rank8 = EmptyOperator(task_id='refresh_ch_rank8')

        sanitycheck_before_refresh8 >> refresh_ch_rank8

    @task_group(group_id='sync_data')
    def tg_sync():

        # push_to_dune = BashOperator(
        #     task_id='overwrite_channel_rank_in_dune_v3',
        #     bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh overwrite_channel_rank_in_dune_v3"
        # )
        push_to_dune = EmptyOperator(task_id='overwrite_channel_rank_in_dune_v3')

        # push_to_s3 = BashOperator(
        #     task_id='backup_channel_rank_s3',
        #     bash_command="cd /pipeline/dags/pg_to_dune && ./upload_to_dune.sh upload_channel_rank_to_s3"
        # )
        push_to_s3 = EmptyOperator(task_id='backup_channel_rank_s3')

        push_to_dune >> push_to_s3

    tg_prep_db() >> tg_compute() >> tg_db() >> tg_sync()


dag = create_dag()

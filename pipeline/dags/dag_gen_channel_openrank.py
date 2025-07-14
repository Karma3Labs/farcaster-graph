import math
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.bash import BashOperator
from airflow.sensors.time_delta import TimeDeltaSensor
from airflow.utils.trigger_rule import TriggerRule
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

default_args = {
    "owner": "karma3labs",
    "retries": 5,
    "retry_delay": timedelta(minutes=2),
    # 'on_failure_callback': [send_alert_discord, send_alert_pagerduty],
}

N_CHUNKS = 100  # Define the number of chunks
# NOTE: Refer to the 'k3l_channel_domains' table to get the category
CATEGORY = "test"

with DAG(
    dag_id="gen_channel_openrank",
    default_args=default_args,
    description="This runs run_globaltrust_pipeline.sh without any optimization",
    start_date=datetime(2024, 8, 16),
    # schedule_interval='0 */6 * * *',
    # schedule_interval=timedelta(hours=6),
    schedule_interval=None,
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:
    mkdir_tmp = BashOperator(
        task_id="mkdir_tmp",
        bash_command="cd /pipeline; mkdir -p previous_compute_input/ && mkdir -p tmp/{{ run_id }}",
        dag=dag,
    )

    @task_group(group_id="openrank_compute_group")
    def tg_openrank_compute():
        fetch_domains = BashOperator(
            task_id="fetch_domains",
            bash_command=(
                "cd /pipeline && ./run_channel_openrank.sh"
                " -w . -v .venv -t fetch_domains"
                f" -s channels/Top_Channels.csv -c {CATEGORY} "
            ),
            do_xcom_push=True,
        )

        @task
        def extract_channel_ids(channel_ids: str) -> list:
            channel_ids_list = channel_ids.split(",")
            print(
                f"Extracted channel IDs (len={len(channel_ids_list)}): {channel_ids_list}"
            )
            chunk_size = (
                math.ceil(len(channel_ids_list) / N_CHUNKS)
                if len(channel_ids_list) >= N_CHUNKS
                else 1
            )
            channel_chunks = [
                channel_ids_list[i : i + chunk_size]
                for i in range(0, len(channel_ids_list), chunk_size)
            ]
            print(
                f"Channel chunks (len={len(channel_chunks)} chunk_len={len(channel_chunks[0])}): {channel_chunks}"
            )
            return channel_chunks

        @task(max_active_tis_per_dagrun=8)
        def gen_domain_files_chunk(chunk: list, run_id):
            chunk_str = ",".join(chunk)
            gen_files_task = BashOperator(
                task_id=f"gen_domain_files_chunk_{hash(chunk_str)}",
                bash_command="cd /pipeline && ./run_channel_openrank.sh"
                " -w . -v .venv -t gen_domain_files"
                f" -s channels/Top_Channels.csv -c {CATEGORY}"
                f" -o tmp/{run_id}"
                f' "{chunk_str}"',
                env={"PYTHONUNBUFFERED": "1"},  # Ensures real-time logging
            )
            gen_files_task.execute({})

        @task(max_active_tis_per_dagrun=8)
        def process_domains_chunk(chunk: list, run_id):
            chunk_str = ",".join(chunk)
            process_task = BashOperator(
                task_id=f"process_domains_chunk_{hash(chunk_str)}",
                bash_command="cd /pipeline && ./run_channel_openrank.sh"
                " -w . -v .venv -t process_domains"
                f" -c {CATEGORY} -o tmp/{run_id}"
                f' "{chunk_str}"',
                env={"PYTHONUNBUFFERED": "1"},  # Ensures real-time logging
            )
            process_task.execute({})

        # Create dynamic tasks
        extract_ids = extract_channel_ids(fetch_domains.output)
        gen_file_tasks = gen_domain_files_chunk.expand(chunk=extract_ids)
        process_tasks = process_domains_chunk.expand(chunk=extract_ids)

        fetch_results = BashOperator(
            task_id="fetch_results",
            bash_command="cd /pipeline && ./run_channel_openrank.sh"
            f" -w . -v .venv -t fetch_results -c {CATEGORY}"
            " -o tmp/{{ run_id }} ",
        )

        (
            fetch_domains
            >> extract_ids
            >> gen_file_tasks
            >> process_tasks
            >> fetch_results
        )

    rmdir_tmp = BashOperator(
        task_id="rmdir_tmp",
        bash_command="cd /pipeline && mv tmp/{{ run_id }}/* previous_compute_input/ && rm -r tmp/{{ run_id }}",
        trigger_rule=TriggerRule.ALL_SUCCESS,
        dag=dag,
    )

    (mkdir_tmp >> tg_openrank_compute() >> rmdir_tmp)

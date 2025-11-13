"""
Token Distribution DAG - Task-based architecture with parallelization.

This DAG implements a scalable architecture with:
- Parallel processing per round (fetch, calculate, verify)
- Serialized transaction submission (nonce management)
- Proper idempotency and error recovery
- Clear task boundaries for observability
- Notification to reward recipients after confirmation

Task Flow:
1. `gather_rounds_due()` → [round_ids]
2. `fetch_leaderboard.expand(round_id)` → [round_data]
3. `calculate.expand(round_data)` → [log_ids]
4. `verify.expand(log_ids, round_id)` → [log_ids]
5. `submit_txs([log_ids])` → [tx_hashes]
6. `wait_for_confirmations(tx_hashes)` → complete
7. `notify_recipients([log_ids])` → complete
"""

import json
from collections.abc import Iterable
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.exceptions import AirflowSkipException
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

from k3l.fcgraph.pipeline import token_distribution_tasks as td_tasks
from k3l.fcgraph.pipeline.token_distribution.models import Log, Round
from k3l.fcgraph.pipeline.token_distribution_tasks import RoundData, RoundLogs

default_args = {
    "owner": "karma3labs",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "max_active_tis_per_dagrun": 3,  # Limit concurrent tasks to prevent DB connection exhaustion
    "on_failure_callback": [send_alert_discord, send_alert_pagerduty],
}

with DAG(
    dag_id="token_distribution",
    default_args=default_args,
    description="Process token distributions with parallel round processing and serial TX submission",
    start_date=datetime(2024, 11, 7),
    schedule_interval=timedelta(minutes=15),  # Check every 15 minutes
    is_paused_upon_creation=True,
    max_active_runs=1,
    catchup=False,
) as dag:

    @task
    def gather_rounds(**context) -> list[dict]:
        data_interval_end = context["data_interval_end"]
        assert isinstance(data_interval_end, datetime)
        return [
            round_.model_dump(mode="json")
            for round_ in td_tasks.gather_rounds_due(data_interval_end)
        ]

    @task
    def collect_round_data(round_: dict) -> dict:
        return td_tasks.collect_round_data(
            Round.model_validate_json(json.dumps(round_))
        ).model_dump(mode="json")

    @task
    def calculate_distributions(round_data: dict) -> list[dict]:
        logs = td_tasks.calculate(RoundData.model_validate_json(json.dumps(round_data)))
        if not logs:
            raise AirflowSkipException("No logs to submit.")
        return [log.model_dump(mode="json") for log in logs]

    @task
    def verify_calculations(logs: list[dict], round_data: dict) -> dict:
        """Airflow task wrapper to verify distributions match budget."""
        round_ = RoundData.model_validate_json(json.dumps(round_data))
        verified_logs = td_tasks.verify(
            [Log.model_validate_json(json.dumps(log)) for log in logs],
            round_,
        )
        return RoundLogs(round_data=round_, logs=verified_logs).model_dump(mode="json")

    # Task to submit transactions
    @task(trigger_rule="none_failed")
    def submit_transactions(round_logs: Iterable[dict]) -> list[dict]:
        rls = [
            RoundLogs.model_validate_json(json.dumps(rl))
            for rl in round_logs or []
            if rl is not None  # filter skipped rounds
        ]
        rls = td_tasks.submit_txs(rls)
        return [rl.model_dump(mode="json") for rl in rls]

    # Task to wait for confirmations
    @task
    def wait_for_tx_confirmations(round_logs: list[dict]) -> list[dict]:
        rls = [RoundLogs.model_validate_json(json.dumps(rl)) for rl in round_logs]
        logs = td_tasks.wait_for_confirmations(rls)
        return [log.model_dump(mode="json") for log in logs]

    # Task to notify recipients
    @task
    def notify_reward_recipients(logs: list[dict]) -> None:
        td_tasks.notify_recipients(
            [Log.model_validate_json(json.dumps(log)) for log in logs]
        )

    # Task group for per-round processing
    @task_group(group_id="process_rounds")
    def process_rounds_group(round_: dict) -> dict:
        round_data = collect_round_data(round_)
        logs = calculate_distributions(round_data=round_data)
        verified_logs = verify_calculations(logs=logs, round_data=round_data)
        return verified_logs

    # Main flow
    rounds = gather_rounds()

    # Process all rounds in parallel
    verified_rounds = process_rounds_group.expand(round_=rounds)

    # Submit all transactions serially (for nonce management)
    submitted_rounds = submit_transactions(verified_rounds)

    # Wait for all confirmations
    logs_confirmed = wait_for_tx_confirmations(submitted_rounds)

    # Notify all recipients after confirmations
    # logs_confirmed creates explicit dependency: notifications only after confirmations
    notify_reward_recipients(logs_confirmed)

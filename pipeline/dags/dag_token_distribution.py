"""
Token Distribution DAG - Task-based architecture with parallelization.

This DAG implements a scalable architecture with:
- Parallel processing per round (fetch, calculate, verify)
- Serialized transaction submission (nonce management)
- Proper idempotency and error recovery via database state
- Clear task boundaries for observability
- Minimal inter-task data serialization (only round IDs)
- Notification to reward recipients after confirmation

Task Flow:
1. `gather_rounds_due()` → [round_ids]
2. `process_rounds_group.expand(round)` → [round_ids] (parallel per round)
   - collect_round_data → calculate → verify → lookup_recipients
3. `submit_txs([round_ids])` → [round_ids] (serial for nonce management)
   - Validates funding, queries DB for logs to submit
4. `wait_for_confirmations([round_ids])` → [round_ids]
   - Uses tx_status field for idempotent retry
5. `notify_recipients([round_ids])` → complete
   - Queries DB for confirmed logs (tx_status = 1)
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task, task_group
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

from k3l.fcgraph.pipeline import token_distribution_tasks as td_tasks
from k3l.fcgraph.pipeline.models import UUID
from k3l.fcgraph.pipeline.token_distribution.models import Round

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
    def collect_round_data(round_: dict) -> str:
        """Fetch leaderboard and insert into the `logs` table."""
        round_id = td_tasks.collect_round_data(
            Round.model_validate_json(json.dumps(round_))
        )
        return str(round_id)

    @task
    def calculate_distributions(round_id: str) -> str:
        """Calculate distribution amounts."""
        calculated_id = td_tasks.calculate(UUID(round_id))
        return str(calculated_id)

    @task
    def verify_calculations(round_id: str) -> str:
        """Verify distributions match budget."""
        verified_id = td_tasks.verify(UUID(round_id))
        return str(verified_id)

    @task
    def lookup_recipient_addresses(round_id: str) -> str:
        """Look up and populate receiver wallet addresses."""
        looked_up_id = td_tasks.lookup_recipients(UUID(round_id))
        return str(looked_up_id)

    # Task to submit transactions
    @task(trigger_rule="none_failed")
    def submit_transactions(round_ids: list[str]) -> list[str]:
        """Submit transactions for all verified rounds."""
        processed_ids = td_tasks.submit_txs(UUID(rid) for rid in round_ids)
        return [str(rid) for rid in processed_ids]

    # Task to wait for confirmations
    @task
    def wait_for_tx_confirmations(round_ids: list[str]) -> list[str]:
        """Wait for transaction confirmations."""
        confirmed_ids = td_tasks.wait_for_confirmations(UUID(rid) for rid in round_ids)
        return [str(rid) for rid in confirmed_ids]

    # Task to notify recipients
    @task
    def notify_reward_recipients(round_ids: list[str]) -> None:
        """Send notifications to reward recipients."""
        td_tasks.notify_recipients([UUID(rid) for rid in round_ids])

    # Task group for per-round processing
    @task_group(group_id="process_rounds")
    def process_rounds_group(round_: dict) -> str:
        """Process a single round: fetch leaderboard, calculate, verify, lookup addresses."""
        round_id = collect_round_data(round_)
        round_id = calculate_distributions(round_id)
        round_id = verify_calculations(round_id)
        round_id = lookup_recipient_addresses(round_id)
        return round_id

    # Main flow
    rounds = gather_rounds()

    # Process all rounds in parallel (returns round IDs)
    verified_round_ids = process_rounds_group.expand(round_=rounds)

    # Submit all transactions serially (for nonce management)
    submitted_round_ids = submit_transactions(verified_round_ids)

    # Wait for all confirmations
    confirmed_round_ids = wait_for_tx_confirmations(submitted_round_ids)

    # Notify all recipients after confirmations
    notify_reward_recipients(confirmed_round_ids)

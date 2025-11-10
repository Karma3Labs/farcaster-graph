"""
Token Distribution DAG - Task-based architecture with parallelization.

This DAG implements a scalable architecture with:
- Parallel processing per round (fetch, calculate, verify)
- Serialized transaction submission (nonce management)
- Proper idempotency and error recovery
- Clear task boundaries for observability

Task Flow:
1. gather_rounds_due() → [round_ids]
2. fetch_leaderboard.expand(round_id) → [round_data]
3. calculate.expand(round_data) → [log_ids]
4. verify.expand(log_ids, round_id) → [log_ids]
5. submit_txs([log_ids]) → [tx_hashes]
6. wait_for_confirmations(tx_hashes) → complete
"""

from datetime import datetime, timedelta
from uuid import UUID

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.empty import EmptyOperator
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

from k3l.fcgraph.pipeline import token_distribution_tasks as td_tasks

default_args = {
    "owner": "karma3labs",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
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
    # Task to gather rounds that are due
    @task
    def gather_rounds(**context) -> list[UUID]:
        """
        Airflow task wrapper to gather rounds due for processing.
        Extracts execution date from Airflow context and passes to business logic.
        """
        data_interval_end = context["data_interval_end"]
        assert isinstance(data_interval_end, datetime)
        return td_tasks.gather_rounds_due(data_interval_end)

    # Task to fetch leaderboard for a specific round
    @task(map_index_template="{{ task.op_kwargs['round_id'] }}")
    def fetch_round_leaderboard(round_id: UUID) -> dict:
        """Airflow task wrapper to fetch leaderboard data."""
        return td_tasks.fetch_leaderboard(round_id)

    # Task to calculate distributions
    @task(map_index_template="{{ task.op_kwargs['round_data']['round_id'] }}")
    def calculate_distributions(round_data: dict) -> list[str]:
        """Airflow task wrapper to calculate and insert distribution logs."""
        return td_tasks.calculate(round_data)

    # Task to verify calculations
    @task(map_index_template="{{ task.op_kwargs['round_data']['round_id'] }}")
    def verify_calculations(log_ids: list[str], round_data: dict) -> list[str]:
        """Airflow task wrapper to verify distributions match budget."""
        return td_tasks.verify(log_ids, round_data["round_id"])

    # Task to submit transactions
    @task(max_active_tis_per_dag=1)  # Ensure only one instance runs at a time
    def submit_transactions(log_ids_nested: list[list[str]]) -> list[str]:
        """Airflow task wrapper to submit blockchain transactions."""
        return td_tasks.submit_txs(log_ids_nested)

    # Task to wait for confirmations
    @task
    def wait_for_tx_confirmations(tx_hashes: list[str]) -> None:
        """Airflow task wrapper to wait for blockchain confirmations."""
        td_tasks.wait_for_confirmations(tx_hashes)

    # Task group for per-round processing
    @task_group(group_id="process_rounds")
    def process_rounds_group(round_ids: list[UUID]):
        """Process each round in parallel."""

        # Fetch leaderboards in parallel
        leaderboards = fetch_round_leaderboard.expand(round_id=round_ids)

        # Calculate distributions in parallel
        log_ids_per_round = calculate_distributions.expand(round_data=leaderboards)

        # Verify calculations in parallel
        # We need to pair log_ids with round_data for verification
        verified_log_ids = verify_calculations.partial().expand(
            log_ids=log_ids_per_round, round_data=leaderboards
        )

        return verified_log_ids

    # Start and end markers
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    # Main flow
    rounds = gather_rounds()

    # Process rounds in parallel if any exist
    # We use a branch to handle the case where no rounds are due
    @task.branch
    def check_rounds(round_ids: list[UUID]) -> str:
        """Check if there are rounds to process."""
        if round_ids:
            return "process_rounds_wrapper"
        else:
            return "no_rounds"

    no_rounds = EmptyOperator(task_id="no_rounds")

    @task_group(group_id="process_rounds_wrapper")
    def process_rounds_wrapper(round_ids: list[UUID]):
        """Wrapper for processing rounds."""
        # Process all rounds in parallel
        verified_logs = process_rounds_group(round_ids)

        # Submit all transactions serially (for nonce management)
        tx_hashes = submit_transactions(verified_logs)

        # Wait for all confirmations
        wait_for_tx_confirmations(tx_hashes)

    # Build the DAG flow
    branch_result = check_rounds(rounds)

    (start >> rounds >> branch_result)

    branch_result >> no_rounds >> end
    branch_result >> process_rounds_wrapper(rounds) >> end

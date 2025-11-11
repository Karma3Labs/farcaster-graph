"""
FIP-2 Tokens Refresh DAG.

This DAG refreshes the fip2_tokens materialized view and populates
missing ERC-20 token metadata in the erc20_tokens table.

Architecture:
    The DAG runs every 5 minutes to ensure token metadata is kept fresh.
    Since both tables are properly indexed, incremental updates are efficient.

Task Flow:
    1. refresh_materialized_view → REFRESH MATERIALIZED VIEW CONCURRENTLY k3l.fip2_tokens
    2. process_missing_tokens → Identify and populate missing tokens in erc20_tokens

Design Decisions:
    - Uses CONCURRENTLY for materialized view refresh to avoid blocking reads
    - Processes only new/missing tokens for efficiency
    - Includes retry logic for blockchain RPC failures
    - Uses chain_index for automatic RPC endpoint discovery

Schedule:
    Every 5 minutes - frequent updates ensure new tokens are quickly discovered
    and metadata is populated promptly.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from hooks.discord import send_alert_discord
from hooks.pagerduty import send_alert_pagerduty

from k3l.fcgraph.pipeline import fip2_token_tasks

# Default arguments for the DAG
default_args = {
    "owner": "k3l",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": lambda context: [
        send_alert_discord(context),
        send_alert_pagerduty(context),
    ],
}

# Create the DAG
with DAG(
    "refresh_fip2_tokens",
    default_args=default_args,
    description="Refresh FIP-2 tokens and populate ERC-20 metadata",
    schedule_interval=timedelta(minutes=5),  # Run every 5 minutes
    max_active_runs=1,  # Prevent overlapping runs
    catchup=False,  # Don't backfill on startup
    tags=["token", "fip2", "erc20", "eigen8"],
) as dag:
    # Task 1: Refresh the materialized view using Python task
    @task(task_id="refresh_materialized_view")
    def refresh_materialized_view(**context) -> None:
        """
        Refresh the fip2_tokens materialized view.

        This task directly executes the SQL to refresh the materialized view
        without using shell scripts.

        :param context: Airflow context dictionary.
        """
        print("Refreshing fip2_tokens materialized view")

        # Use the business logic function that already handles the database connection
        import asyncio

        from k3l.fcgraph.pipeline import fip2_token_tasks

        try:
            asyncio.run(fip2_token_tasks.refresh_fip2_tokens_view())
            print("Successfully refreshed fip2_tokens materialized view")
        except Exception as e:
            print(f"Failed to refresh materialized view: {e}")
            raise

    # Create the task instance
    refresh_view = refresh_materialized_view()

    # Task 2: Identify missing tokens and prepare batches
    @task(task_id="identify_and_batch_tokens")
    def identify_and_batch_tokens(**context) -> list[dict]:
        """
        Identify missing tokens and prepare batches for parallel processing.

        This task:
        1. Queries tokens in fip2_tokens not present in erc20_tokens
        2. Filters out special addresses (native assets, null address, etc.)
        3. Groups tokens by chain_id
        4. Splits into batches of TOKEN_QUERY_BATCH_SIZE

        :param context: Airflow context dictionary.
        :return: List of batch dictionaries for dynamic task mapping.
        """
        import asyncio

        from k3l.fcgraph.pipeline import fip2_token_tasks

        print("Identifying missing tokens and preparing batches")

        # Fetch missing tokens
        missing_tokens = asyncio.run(fip2_token_tasks.fetch_missing_tokens())
        print(f"Found {len(missing_tokens)} missing tokens")

        if not missing_tokens:
            return []

        # Filter out special addresses and unsupported chains before batching
        special_addresses = {
            "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",  # EIP-7528 native asset
            "0x0000000000000000000000000000000000000000",  # Null address
            "0xffffffffffffffffffffffffffffffffffffffff",  # Sometimes used for native
        }

        # Check which chains have RPC support or are known to be problematic
        chains_to_skip = set()
        for chain_id, _ in missing_tokens:
            if chain_id not in chains_to_skip:
                # Check if it's a known problematic chain
                if fip2_token_tasks.is_problematic_chain(chain_id):
                    chains_to_skip.add(chain_id)
                    print(
                        f"  Chain {chain_id} is known to be problematic, will filter out all tokens"
                    )
                # Check if it has RPC support
                elif not fip2_token_tasks.get_rpc_urls_for_chain(chain_id):
                    chains_to_skip.add(chain_id)
                    print(
                        f"  No RPC support for chain {chain_id}, will filter out all tokens"
                    )

        filtered_tokens = []
        skipped_special = 0
        skipped_no_rpc = 0

        for chain_id, address in missing_tokens:
            if address.lower() in special_addresses:
                print(f"  Filtering out special address: {address}")
                skipped_special += 1
            elif chain_id in chains_to_skip:
                # Don't log each token, just count them
                skipped_no_rpc += 1
            else:
                filtered_tokens.append((chain_id, address))

        print(
            f"Filtered out {skipped_special} special addresses and "
            f"{skipped_no_rpc} tokens from unsupported chains, "
            f"{len(filtered_tokens)} tokens remaining"
        )

        if not filtered_tokens:
            print("No tokens remaining after filtering special addresses")
            return []

        # Prepare batches for dynamic task mapping
        batches = fip2_token_tasks.prepare_token_batches(filtered_tokens)
        print(f"Prepared {len(batches)} batches for processing")

        for batch in batches[:5]:  # Show first 5 batches as examples
            print(f"  Batch {batch['task_id']}: {len(batch['addresses'])} tokens")

        return batches

    # Task 3: Process token batches in parallel using dynamic task mapping
    @task(
        task_id="process_token_batch",
        map_index_template="{{ task.op_kwargs['batch']['task_id'] }}",
    )
    def process_token_batch(batch: dict, **context) -> dict:
        """
        Process a single batch of tokens.

        This task fetches metadata for tokens using Multicall3 and inserts
        into the database immediately (batch commit).

        :param batch: Batch dictionary with chain_id and addresses.
        :param context: Airflow context dictionary.
        :return: Processing result summary.
        """
        from k3l.fcgraph.pipeline import fip2_token_tasks

        task_id = batch["task_id"]
        print(
            f"Processing batch {task_id}: {len(batch['addresses'])} tokens on chain {batch['chain_id']}"
        )

        try:
            # Process the batch
            result = fip2_token_tasks.run_process_batch(batch)

            # Log results
            if result["status"] == "success":
                print(
                    f"Batch {task_id} completed: {result['tokens_inserted']} tokens inserted"
                )
            else:
                print(
                    f"Batch {task_id} failed with expected error: {result.get('error', 'Unknown error')}"
                )
                # Expected errors (DB/RPC issues) - don't raise, let other batches continue

            return result

        except Exception as e:
            # Unexpected errors (programming bugs) should fail the task
            print(f"Batch {task_id} failed with UNEXPECTED error: {e}")
            raise  # This will fail the task and alert operators

    # Task 4: Summarize results
    @task(task_id="summarize_results")
    def summarize_results(batch_results: list[dict], **context) -> dict:
        """
        Summarize the results from all batch processing tasks.

        :param batch_results: List of results from all batch tasks.
        :param context: Airflow context dictionary.
        :return: Overall summary.
        """
        total_processed = 0
        total_fetched = 0
        total_inserted = 0
        total_skipped_existing = 0
        total_failed = 0
        failed_batches = []

        for result in batch_results:
            if result["status"] == "success":
                total_processed += result["tokens_processed"]
                total_fetched += result.get("tokens_fetched", 0)
                total_inserted += result["tokens_inserted"]
                total_skipped_existing += result.get("tokens_skipped_existing", 0)
                total_failed += result.get("tokens_failed", 0)
            else:
                failed_batches.append(result["task_id"])

        print(f"Processing complete:")
        print(f"  Total tokens attempted: {total_processed}")
        print(f"  Successfully fetched: {total_fetched}")
        print(f"  Newly inserted: {total_inserted}")
        print(f"  Already existed (skipped): {total_skipped_existing}")
        print(f"  Failed to fetch: {total_failed}")
        print(f"  Failed batches: {len(failed_batches)}")

        if failed_batches:
            print(f"  Failed batch IDs: {', '.join(failed_batches[:10])}")
            if len(failed_batches) > 10:
                print(f"    ... and {len(failed_batches) - 10} more")

        return {
            "total_processed": total_processed,
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_skipped_existing": total_skipped_existing,
            "total_failed": total_failed,
            "failed_batches": len(failed_batches),
            "success": len(failed_batches) == 0,
        }

    # Create task instances and set dependencies
    batches = identify_and_batch_tokens()

    # Dynamic task mapping - process batches in parallel
    # Each batch becomes a separate task instance
    batch_results = process_token_batch.expand(batch=batches)

    # Summarize all results
    summary = summarize_results(batch_results)

    # Set the dependency chain
    refresh_view >> batches >> batch_results >> summary

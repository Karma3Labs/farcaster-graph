"""
FIP-2 Token Refresh Tasks.

This module handles the refresh and population of FIP-2 token metadata:
1. Refreshing the fip2_tokens materialized view
2. Identifying tokens missing from erc20_tokens table
3. Fetching ERC-20 token metadata from blockchain
4. Populating erc20_tokens table with fetched data

The module uses asyncpg for database operations and Web3 with chain_index
for blockchain interactions. It supports multiple chains and includes
retry logic for RPC failures.

Task Flow:
    1. refresh_fip2_tokens_view() → Refresh materialized view
    2. fetch_missing_tokens() → Identify tokens not in erc20_tokens
    3. fetch_token_metadata() → Get metadata from blockchain
    4. insert_token_metadata() → Populate erc20_tokens table
"""

import asyncio
import json
import logging
from itertools import islice
from typing import Any

import asyncpg
from chain_index import get_chain_info
from eth_typing import ChecksumAddress
from eth_utils import to_bytes, to_checksum_address, to_hex
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception

from config import settings

logger = logging.getLogger(__name__)

# Special addresses that should be filtered out
SPECIAL_ADDRESSES = {
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",  # EIP-7528 native asset placeholder
    "0x0000000000000000000000000000000000000000",  # Null address
    "0xffffffffffffffffffffffffffffffffffffffff",  # Sometimes used for native asset
}

# Chains that are known to be problematic or unsupported
PROBLEMATIC_CHAINS = {
    999,  # HyperEVM - incorrect/unstable RPC endpoints
}


def is_special_address(address: ChecksumAddress) -> bool:
    """Check if an address is a special placeholder that should be skipped."""
    return address.lower() in SPECIAL_ADDRESSES


def is_problematic_chain(chain_id: int) -> bool:
    """Check if a chain is known to be problematic."""
    return chain_id in PROBLEMATIC_CHAINS


# Minimal ERC-20 ABI for fetching token metadata
ERC20_ABI = json.loads("""[
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]""")

# Multicall3 ABI - only the aggregate3 function we need
MULTICALL3_ABI = json.loads("""[
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"}
                ],
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]""")


async def get_db_connection() -> asyncpg.Connection:
    """
    Create a connection to the eigen8 database using ALT_DB settings.

    :return: Database connection object.
    """
    return await asyncpg.connect(
        user=settings.ALT_DB_USER,
        password=settings.ALT_DB_PASSWORD.get_secret_value(),
        database=settings.ALT_DB_NAME,
        host=settings.ALT_DB_HOST,
        port=settings.ALT_DB_PORT,
    )


async def refresh_fip2_tokens_view() -> None:
    """
    Refresh the fip2_tokens materialized view.

    This function executes REFRESH MATERIALIZED VIEW CONCURRENTLY
    to update the view without blocking reads.

    :raises asyncpg.PostgresError: If database operation fails.
    """
    logger.info("Refreshing fip2_tokens materialized view")

    conn = await get_db_connection()
    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY k3l.fip2_tokens")
        logger.info("Successfully refreshed fip2_tokens materialized view")
    except asyncpg.PostgresError as e:
        logger.error("Failed to refresh fip2_tokens view", exc_info=True)
        raise
    finally:
        await conn.close()


async def fetch_missing_tokens() -> list[tuple[int, ChecksumAddress]]:
    """
    Identify tokens present in fip2_tokens but missing from erc20_tokens.

    :return: List of (chain_id, address) tuples for missing tokens.
    """
    logger.info("Fetching missing tokens from erc20_tokens")

    conn = await get_db_connection()
    try:
        # Query to find tokens in fip2_tokens not in erc20_tokens
        query = """
            SELECT f.chain_id, f.address
            FROM k3l.fip2_tokens f
            LEFT JOIN k3l.erc20_tokens e
                ON f.chain_id = e.chain_id AND f.address = e.address
            WHERE e.chain_id IS NULL
            ORDER BY f.chain_id, f.address
        """

        rows = await conn.fetch(query)
        # Convert bytes addresses to ChecksumAddress at the edge
        missing_tokens = [
            (row["chain_id"], to_checksum_address(row["address"])) for row in rows
        ]

        logger.info(f"Found {len(missing_tokens)} tokens missing from erc20_tokens")
        return missing_tokens

    except asyncpg.PostgresError as e:
        logger.error("Failed to fetch missing tokens", exc_info=True)
        raise
    finally:
        await conn.close()


def get_rpc_urls_for_chain(chain_id: int) -> list[str]:
    """
    Get RPC URLs for a given chain ID using chain_index.

    :param chain_id: The blockchain chain ID.
    :return: List of HTTPS RPC URLs for the chain.
    """
    # Known good RPCs that should be prioritized or used instead of chain-index
    known_good_rpcs = {
        1: [
            "https://eth.llamarpc.com",
            "https://ethereum-rpc.publicnode.com",
        ],  # Ethereum mainnet
        10: [
            "https://mainnet.optimism.io",
            "https://optimism-rpc.publicnode.com",
        ],  # Optimism
        8453: ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],  # Base
        42161: [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum-one-rpc.publicnode.com",
        ],  # Arbitrum One
        # Note: Chain 999 (HyperEVM) removed - no working public RPC found
    }

    # If we have known good RPCs, use them
    if chain_id in known_good_rpcs:
        logger.debug(f"Using known good RPCs for chain {chain_id}")
        return known_good_rpcs[chain_id]

    # Otherwise try chain-index
    try:
        chain_info = get_chain_info(chain_id)
        if chain_info and hasattr(chain_info, "rpc"):
            # Filter for HTTPS URLs only (ignore WSS and other schemes)
            rpcs = [url for url in chain_info.rpc if url.startswith("https://")]
            if rpcs:
                return rpcs
    except Exception as e:
        logger.warning(f"Failed to get chain info for chain_id {chain_id}: {e}")

    # No RPCs found
    return []


async def fetch_token_metadata_from_chain(
    chain_id: int, token_address: ChecksumAddress, rpc_urls: list[str]
) -> dict[str, Any] | None:
    """
    Fetch ERC-20 token metadata from blockchain.

    :param chain_id: The blockchain chain ID.
    :param token_address: The token contract address.
    :param rpc_urls: List of RPC URLs to try.
    :return: Token metadata dict or None if all attempts fail.
    """
    # Check for special addresses (should already be filtered at DAG level)
    if is_special_address(token_address):
        logger.info(f"Skipping special address {token_address} on chain {chain_id}")
        return None

    for rpc_url in rpc_urls:
        try:
            logger.debug(
                f"Trying RPC {rpc_url} for token {token_address} on chain {chain_id}"
            )

            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            if not w3.is_connected():
                logger.debug(f"Failed to connect to {rpc_url}")
                continue

            # First check if contract exists
            try:
                code = w3.eth.get_code(token_address)
                if code == b"" or code == "0x":
                    logger.warning(
                        f"No contract at {token_address} on chain {chain_id}"
                    )
                    return None
                elif len(code) < 10:  # Very short bytecode is suspicious
                    logger.warning(
                        f"Suspicious contract bytecode length {len(code)} for {token_address} on chain {chain_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to get code for {token_address}: {e}")
                # Continue to try the actual calls anyway

            contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)

            # Fetch token metadata
            symbol = None
            name = None
            symbol_error = None
            name_error = None

            try:
                symbol = contract.functions.symbol().call()
            except ContractLogicError as e:
                # This usually means the method doesn't exist or reverted
                symbol_error = f"ContractLogicError: {e}"
            except Web3Exception as e:
                # Check for specific error codes
                error_str = str(e)
                if "-32603" in error_str:
                    symbol_error = f"RPC Internal Error (-32603): Likely complex contract or RPC issue"
                elif "-32000" in error_str:
                    symbol_error = (
                        f"Execution reverted (-32000): Contract rejected the call"
                    )
                else:
                    symbol_error = f"Web3Exception: {e}"
            except Exception as e:
                symbol_error = f"Unexpected error: {type(e).__name__}: {e}"

            try:
                name = contract.functions.name().call()
            except ContractLogicError as e:
                # This usually means the method doesn't exist or reverted
                name_error = f"ContractLogicError: {e}"
            except Web3Exception as e:
                # Check for specific error codes
                error_str = str(e)
                if "-32603" in error_str:
                    name_error = f"RPC Internal Error (-32603): Likely complex contract or RPC issue"
                elif "-32000" in error_str:
                    name_error = (
                        f"Execution reverted (-32000): Contract rejected the call"
                    )
                else:
                    name_error = f"Web3Exception: {e}"
            except Exception as e:
                name_error = f"Unexpected error: {type(e).__name__}: {e}"

            # Only return if we got at least some valid metadata
            if symbol or name:
                return {
                    "chain_id": chain_id,
                    "address": token_address,
                    "symbol": symbol[:32] if symbol else "",  # Empty string as fallback
                    "description": name[:256]
                    if name
                    else "",  # Empty string as fallback
                }
            else:
                # No metadata found, log detailed errors
                logger.warning(
                    f"No metadata for token {token_address} on chain {chain_id}:\n"
                    f"  Symbol error: {symbol_error}\n"
                    f"  Name error: {name_error}"
                )
                return None

        except Exception as e:
            logger.debug(f"Failed to fetch from {rpc_url}: {e}")
            continue

    # All RPCs failed
    logger.warning(
        f"Failed to fetch metadata for token {token_address} on chain {chain_id}"
    )
    return None


async def fetch_token_metadata(
    missing_tokens: list[tuple[int, ChecksumAddress]],
) -> list[dict[str, Any]]:
    """
    Fetch metadata for all missing tokens from blockchain.

    :param missing_tokens: List of (chain_id, address) tuples.
    :return: List of token metadata dictionaries.
    """
    logger.info(f"Fetching metadata for {len(missing_tokens)} tokens")

    # Group tokens by chain_id for efficiency
    tokens_by_chain: dict[int, list[ChecksumAddress]] = {}
    for chain_id, address in missing_tokens:
        if chain_id not in tokens_by_chain:
            tokens_by_chain[chain_id] = []
        tokens_by_chain[chain_id].append(address)

    metadata_list = []

    for chain_id, addresses in tokens_by_chain.items():
        rpc_urls = get_rpc_urls_for_chain(chain_id)
        if not rpc_urls:
            logger.warning(f"No RPC URLs available for chain {chain_id}")
            continue

        logger.info(f"Fetching {len(addresses)} tokens from chain {chain_id}")

        # Process tokens for this chain
        for checksum_address in addresses:
            metadata = await fetch_token_metadata_from_chain(
                chain_id, checksum_address, rpc_urls
            )

            if metadata:
                # Address is already ChecksumAddress in metadata
                metadata_list.append(metadata)
            else:
                # Skip tokens that failed to fetch - they'll be retried next run
                logger.debug(f"Skipping token {checksum_address} - fetch failed")

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

    logger.info(f"Successfully fetched metadata for {len(metadata_list)} tokens")
    return metadata_list


async def insert_token_metadata(token_metadata: list[dict[str, Any]]) -> int:
    """
    Insert token metadata into erc20_tokens table.

    :param token_metadata: List of token metadata dictionaries with ChecksumAddress.
    :return: Number of tokens inserted.
    :raises asyncpg.PostgresError: If database operation fails.
    """
    if not token_metadata:
        logger.info("No token metadata to insert")
        return 0

    logger.info(f"Inserting {len(token_metadata)} tokens into erc20_tokens")

    conn = await get_db_connection()
    try:
        # Prepare the insert statement with ON CONFLICT DO NOTHING for idempotency
        insert_query = """
            INSERT INTO k3l.erc20_tokens (chain_id, address, symbol, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chain_id, address) DO NOTHING
        """

        # Convert metadata to tuples for batch insert
        # Convert ChecksumAddress to bytes at the edge (database boundary)
        values = [
            (
                token["chain_id"],
                to_bytes(hexstr=token["address"]),  # Convert ChecksumAddress to bytes
                token["symbol"],
                token["description"],
            )
            for token in token_metadata
        ]

        # Execute batch insert
        result = await conn.executemany(insert_query, values)

        # Parse the result to get insert count
        # Format: "INSERT 0 N" where N is the number of inserted rows
        inserted_count = int(result.split()[-1]) if result else 0

        skipped_count = len(token_metadata) - inserted_count
        if skipped_count > 0:
            logger.info(
                f"Inserted {inserted_count} new tokens, skipped {skipped_count} existing tokens in erc20_tokens"
            )
        else:
            logger.info(
                f"Successfully inserted {inserted_count} new tokens into erc20_tokens"
            )
        return inserted_count

    except asyncpg.PostgresError as e:
        logger.error("Failed to insert token metadata", exc_info=True)
        raise
    finally:
        await conn.close()


def prepare_token_batches(
    missing_tokens: list[tuple[int, ChecksumAddress]],
) -> list[dict[str, Any]]:
    """
    Prepare token batches for dynamic task mapping.

    Groups tokens by chain and splits into batches of TOKEN_QUERY_BATCH_SIZE.

    :param missing_tokens: List of (chain_id, address) tuples.
    :return: List of batch dictionaries for task mapping.
    """
    if not missing_tokens:
        return []

    # Sort tokens by (chain_id, address) for consistent ordering
    sorted_tokens = sorted(missing_tokens, key=lambda x: (x[0], x[1].lower()))

    # Group by chain_id
    tokens_by_chain: dict[int, list[ChecksumAddress]] = {}
    for chain_id, address in sorted_tokens:
        if chain_id not in tokens_by_chain:
            tokens_by_chain[chain_id] = []
        tokens_by_chain[chain_id].append(address)

    # Create batches
    batches = []
    batch_size = settings.TOKEN_QUERY_BATCH_SIZE

    for chain_id, addresses in tokens_by_chain.items():
        # Split addresses into chunks
        for i in range(0, len(addresses), batch_size):
            batch_addresses = addresses[i : i + batch_size]

            # Create task identifier
            first_addr = batch_addresses[0][:10]
            last_addr = batch_addresses[-1][:10]
            task_id = f"{chain_id}/{first_addr}-{last_addr}"

            batches.append(
                {
                    "task_id": task_id,
                    "chain_id": chain_id,
                    "addresses": batch_addresses,
                }
            )

    logger.info(f"Prepared {len(batches)} batches from {len(missing_tokens)} tokens")
    return batches


async def fetch_token_batch_multicall(
    chain_id: int,
    token_addresses: list[ChecksumAddress],
    rpc_urls: list[str],
) -> list[dict[str, Any]]:
    """
    Fetch metadata for a batch of tokens using Multicall3.

    :param chain_id: The blockchain chain ID.
    :param token_addresses: List of token addresses to query.
    :param rpc_urls: List of RPC URLs to try.
    :return: List of token metadata dictionaries.
    """
    # Note: Special addresses should already be filtered at the DAG level
    # but we'll still check for the native asset in results
    multicall_address = settings.get_multicall3_address(chain_id)

    for rpc_url in rpc_urls:
        try:
            logger.debug(
                f"Trying Multicall3 on {rpc_url} for {len(token_addresses)} tokens"
            )

            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
            if not w3.is_connected():
                continue

            # Create multicall contract
            multicall = w3.eth.contract(
                address=to_checksum_address(multicall_address), abi=MULTICALL3_ABI
            )

            # Prepare calls for each token (symbol and name)
            calls = []
            for token_addr in token_addresses:
                token = w3.eth.contract(address=token_addr, abi=ERC20_ABI)

                # Add symbol() call
                calls.append(
                    {
                        "target": token_addr,
                        "allowFailure": True,
                        "callData": token.encodeABI(fn_name="symbol", args=[]),
                    }
                )

                # Add name() call
                calls.append(
                    {
                        "target": token_addr,
                        "allowFailure": True,
                        "callData": token.encodeABI(fn_name="name", args=[]),
                    }
                )

            # Execute multicall
            results = multicall.functions.aggregate3(calls).call()

            # Process results
            metadata_list = []
            for i, token_addr in enumerate(token_addresses):
                symbol_result = results[i * 2]
                name_result = results[i * 2 + 1]

                # Decode symbol
                symbol = None
                symbol_error = None
                if symbol_result[0]:  # success
                    try:
                        symbol = w3.codec.decode(["string"], symbol_result[1])[0]
                    except Exception as e:
                        symbol_error = f"Decode error: {e}"
                else:
                    # Log the raw error data for debugging
                    symbol_error = f"Call failed, returnData: {symbol_result[1].hex() if symbol_result[1] else 'empty'}"

                # Decode name
                name = None
                name_error = None
                if name_result[0]:  # success
                    try:
                        name = w3.codec.decode(["string"], name_result[1])[0]
                    except Exception as e:
                        name_error = f"Decode error: {e}"
                else:
                    # Log the raw error data for debugging
                    name_error = f"Call failed, returnData: {name_result[1].hex() if name_result[1] else 'empty'}"

                # Only add tokens that have at least a symbol or name
                if symbol or name:
                    metadata_list.append(
                        {
                            "chain_id": chain_id,
                            "address": token_addr,
                            "symbol": symbol[:32]
                            if symbol
                            else "",  # Use empty string as fallback
                            "description": name[:256]
                            if name
                            else "",  # Use empty string as fallback
                        }
                    )
                else:
                    # Log warning - special addresses should have been filtered at DAG level
                    logger.warning(
                        f"No metadata via Multicall3 for {token_addr} on chain {chain_id}:\n"
                        f"  Symbol: {symbol_error}\n"
                        f"  Name: {name_error}"
                    )

            logger.info(
                f"Successfully fetched {len(metadata_list)} tokens via Multicall3"
            )
            return metadata_list

        except Exception as e:
            logger.debug(f"Multicall3 failed on {rpc_url}: {e}")
            continue

    # If all Multicall3 attempts fail, fall back to individual queries
    logger.warning(
        f"Multicall3 failed for chain {chain_id}, falling back to individual queries"
    )
    metadata_list = []

    # Get rate limit delay from config
    delay = settings.RPC_RATE_LIMIT_DELAY

    if delay > 0:
        logger.info(
            f"Using {delay}s delay between individual RPC calls to avoid rate limiting"
        )

    for i, token_addr in enumerate(token_addresses):
        # Add delay between calls to avoid rate limiting (except for the first call)
        if i > 0 and delay > 0:
            await asyncio.sleep(delay)

        # Special addresses should already be filtered at DAG level
        metadata = await fetch_token_metadata_from_chain(chain_id, token_addr, rpc_urls)
        if metadata:
            # Check if the metadata is valid
            symbol = metadata.get("symbol", "")
            description = metadata.get("description", "")
            if symbol or description:
                metadata_list.append(metadata)
            else:
                logger.warning(f"Skipping token {token_addr} - empty metadata returned")
        else:
            logger.warning(
                f"Skipping token {token_addr} - all individual fetch attempts failed"
            )

    return metadata_list


async def process_token_batch(batch: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single batch of tokens - fetch metadata and insert into database.

    This function is designed to be called by Airflow dynamic task mapping.
    It processes one batch independently and commits immediately.

    :param batch: Batch dictionary with chain_id and addresses.
    :return: Processing result summary.
    """
    chain_id = batch["chain_id"]
    addresses = batch["addresses"]
    task_id = batch["task_id"]

    logger.info(
        f"Processing batch {task_id}: {len(addresses)} tokens on chain {chain_id}"
    )

    try:
        # Get RPC URLs for this chain
        rpc_urls = get_rpc_urls_for_chain(chain_id)
        if not rpc_urls:
            logger.error(f"No RPC URLs available for chain {chain_id}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": f"No RPC URLs for chain {chain_id}",
                "tokens_processed": 0,
            }

        # Fetch metadata using Multicall3
        metadata_list = await fetch_token_batch_multicall(chain_id, addresses, rpc_urls)

        # Insert into database immediately (batch commit)
        inserted_count = await insert_token_metadata(metadata_list)

        # Calculate statistics
        fetched_count = len(metadata_list)
        failed_count = len(addresses) - fetched_count
        skipped_existing = fetched_count - inserted_count

        logger.info(
            f"Batch {task_id} complete: "
            f"{fetched_count}/{len(addresses)} fetched, "
            f"{inserted_count} new, "
            f"{skipped_existing} already existed, "
            f"{failed_count} failed"
        )

        return {
            "task_id": task_id,
            "status": "success",
            "tokens_processed": len(addresses),
            "tokens_fetched": fetched_count,
            "tokens_inserted": inserted_count,
            "tokens_skipped_existing": skipped_existing,
            "tokens_failed": failed_count,
        }

    except (asyncpg.PostgresError, Web3Exception) as e:
        # Expected exceptions from database or blockchain operations
        logger.error(
            f"Error processing batch {task_id}: {e.__class__.__name__}", exc_info=True
        )
        return {
            "task_id": task_id,
            "status": "error",
            "error": f"{e.__class__.__name__}: {str(e)}",
            "tokens_processed": 0,
            "tokens_fetched": 0,
            "tokens_inserted": 0,
            "tokens_skipped_existing": 0,
            "tokens_failed": len(addresses),
        }
    except Exception as e:
        # Unexpected exceptions should fail hard - likely programming errors
        logger.critical(
            f"Unexpected error in batch {task_id} - this is likely a bug!",
            exc_info=True,
        )
        raise  # Re-raise to fail the task


def run_process_batch(batch: dict[str, Any]) -> dict[str, Any]:
    """
    Sync wrapper for processing a token batch.

    :param batch: Batch dictionary.
    :return: Processing result.
    """
    return asyncio.run(process_token_batch(batch))


async def process_fip2_tokens() -> dict[str, Any]:
    """
    Main processing function that orchestrates the entire workflow.

    :return: Summary of processing results.
    """
    logger.info("Starting FIP-2 token processing")

    try:
        # Step 1: Refresh the materialized view
        await refresh_fip2_tokens_view()

        # Step 2: Identify missing tokens
        missing_tokens = await fetch_missing_tokens()

        if not missing_tokens:
            logger.info("No missing tokens found, processing complete")
            return {
                "status": "success",
                "missing_tokens_found": 0,
                "tokens_inserted": 0,
            }

        # Step 3: Fetch metadata from blockchain
        token_metadata = await fetch_token_metadata(missing_tokens)

        # Step 4: Insert metadata into database
        inserted_count = await insert_token_metadata(token_metadata)

        logger.info(
            f"FIP-2 token processing complete. "
            f"Found {len(missing_tokens)} missing, "
            f"fetched {len(token_metadata)} metadata, "
            f"inserted {inserted_count} new tokens"
        )

        return {
            "status": "success",
            "missing_tokens_found": len(missing_tokens),
            "tokens_fetched": len(token_metadata),
            "tokens_inserted": inserted_count,
        }

    except Exception as e:
        logger.error("FIP-2 token processing failed", exc_info=True)
        return {"status": "error", "error": str(e)}


# Wrapper functions for Airflow tasks (sync interface)
def run_refresh_view() -> None:
    """Sync wrapper for refreshing materialized view."""
    asyncio.run(refresh_fip2_tokens_view())


def run_process_tokens() -> dict[str, Any]:
    """Sync wrapper for processing tokens."""
    return asyncio.run(process_fip2_tokens())

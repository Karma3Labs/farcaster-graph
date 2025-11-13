import logging
import time
from typing import Protocol

from chain_index import get_chain_info
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import TransactionNotFound

from config import settings

logger = logging.getLogger(__name__)


def get_rpc_url_for_chain(chain_id: int) -> str:
    """
    Get RPC URL for a given chain ID.

    Uses chain_index for public RPCs by default, with optional override from settings.

    :param chain_id: The blockchain chain ID
    :return: HTTPS RPC URL for the chain
    :raises ValueError: If no RPC URL found for chain
    """
    # Check for override in settings
    if chain_id in settings.ETH_RPC_URLS:
        logger.debug(f"Using override RPC URL for chain {chain_id}")
        return settings.ETH_RPC_URLS[chain_id]

    # Otherwise try chain-index
    try:
        chain_info = get_chain_info(chain_id)
        if chain_info and hasattr(chain_info, "rpc"):
            # Filter for HTTPS URLs only (ignore WSS and other schemes)
            rpcs = [url for url in chain_info.rpc if url.startswith("https://")]
            if rpcs:
                logger.debug(f"Using chain_index RPC for chain {chain_id}")
                return rpcs[0]  # Use first HTTPS RPC
    except Exception as e:
        logger.warning(f"Failed to get chain info for chain_id {chain_id}: {e}")

    # No RPC found
    raise ValueError(f"No RPC URL found for chain_id {chain_id}")


class TransactionSubmitter(Protocol):
    """Protocol for submitting blockchain transactions."""

    def get_nonce(self, address: ChecksumAddress) -> int:
        """Get current nonce for address."""
        ...

    def get_gas_price(self) -> int:
        """Get current gas price."""
        ...

    def submit_transaction(
        self,
        to: ChecksumAddress,
        data: str,
        nonce: int,
        gas: int,
        gas_price: int,
    ) -> HexBytes:
        """Submit a transaction and return tx hash."""
        ...

    def wait_for_confirmation(self, tx_hash: HexBytes, timeout_seconds: int) -> dict:
        """Wait for transaction confirmation and return receipt."""
        ...


class Web3TransactionSubmitter:
    """Production implementation using Web3 for blockchain transactions."""

    def __init__(
        self,
        chain_id: int | None = None,
        rpc_url: str | None = None,
        private_key: str | None = None,
    ):
        """
        Initialize Web3 transaction submitter.

        :param chain_id: Chain ID to determine RPC URL (required if rpc_url not provided)
        :param rpc_url: Explicit RPC URL (overrides chain_id lookup)
        :param private_key: Private key for signing (defaults to settings key)
        :raises ValueError: If neither chain_id nor rpc_url provided
        """
        # Determine RPC URL
        if rpc_url:
            self.rpc_url = rpc_url
            self.chain_id = chain_id  # May be None if rpc_url explicitly provided
        elif chain_id:
            self.rpc_url = get_rpc_url_for_chain(chain_id)
            self.chain_id = chain_id
        else:
            raise ValueError("Either chain_id or rpc_url must be provided")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = self.w3.eth.account.from_key(
            private_key
            or settings.CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY.get_secret_value()
        )

        # Get chain_id from network if not provided
        if self.chain_id is None:
            self.chain_id = self.w3.eth.chain_id

        logger.info(
            f"Initialized Web3TransactionSubmitter for chain {self.chain_id} using {self.rpc_url}"
        )

    def get_nonce(self, address: ChecksumAddress) -> int:
        """Get current nonce for address."""
        return self.w3.eth.get_transaction_count(address, "pending")

    def get_gas_price(self) -> int:
        """Get current gas price."""
        return self.w3.eth.gas_price

    def submit_transaction(
        self,
        to: ChecksumAddress,
        data: str,
        nonce: int,
        gas: int,
        gas_price: int,
    ) -> HexBytes:
        """Submit a transaction and return tx hash."""
        tx = {
            "nonce": nonce,
            "to": to,
            "data": data,
            "gas": gas,
            "gasPrice": gas_price,
            "chainId": self.chain_id,
        }

        signed_tx = self.account.sign_transaction(tx)
        return self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    def wait_for_confirmation(self, tx_hash: HexBytes, timeout_seconds: int) -> dict:
        """Wait for transaction confirmation and return receipt."""
        max_retries = timeout_seconds // 5
        retries = 0

        while retries < max_retries:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt["status"] == 1:
                    return receipt
                else:
                    raise ValueError(f"Transaction {tx_hash.to_0x_hex()} was reverted!")
            except TransactionNotFound:
                retries += 1
                if retries >= max_retries:
                    raise TimeoutError(
                        f"Transaction {tx_hash.to_0x_hex()} not confirmed after {timeout_seconds} seconds"
                    )
                time.sleep(5)

        raise TimeoutError(
            f"Transaction {tx_hash.to_0x_hex()} not confirmed after {timeout_seconds} seconds"
        )


def fix_double_encoded_address(
    address_bytes: bytes | memoryview | None,
) -> ChecksumAddress | None:
    """
    Fix Neynar's buggy double-encoded addresses.

    Sometimes Neynar stores ASCII bytes of the hex string instead of raw bytes.
    E.g., instead of ``b'\\x00\\x00...'`` they store ``b'0x0000...'`` as ASCII.

    :param address_bytes: Raw bytes/memoryview from the database (could be double-encoded)
    :return: Valid checksum address or None if invalid
    """
    if not address_bytes:
        return None

    # First, try normal conversion (for correctly stored addresses)
    try:
        return to_checksum_address(address_bytes)
    except (TypeError, ValueError):
        pass

    # If that fails, check if it's double-encoded ASCII
    if isinstance(address_bytes, memoryview):
        address_bytes = address_bytes.tobytes()

    try:
        address_str = address_bytes.decode("ascii")
    except UnicodeDecodeError:  # Expected for non-ASCII bytes
        pass
    else:
        # Decoding succeeded, check if it's a hex-encoded address
        address_without_0x = address_str.lower().removeprefix("0x")
        if len(address_without_0x) == 40 and all(
            c in "0123456789abcdef" for c in address_without_0x
        ):
            # This is double-encoded, convert the string to address
            return to_checksum_address("0x" + address_without_0x)
        # Decoding succeeded, but it's not a hex address - continue to other cases

    # Out of all options
    logger.warning(f"Could not parse address from database: {address_bytes!r}")
    return None

import os
import subprocess
import hvac

from pathlib import Path
from config import settings
from loguru import logger
from hvac.exceptions import VaultError


def get_openrank_mnemonic(self) -> str:
    """
    Fetch the OpenRank mnemonic from vault dynamically.
    The private key is never stored in persistent storage and is fetched fresh each time.

    Returns:
        str: The mnemonic phrase from vault

    Raises:
        ValueError: If vault authentication fails or secret cannot be retrieved
    """
    if settings.OPENRANK_VAULT_URL == "CHANGEME":
        raise ValueError("OPENRANK_VAULT_URL must be configured")

    if settings.OPENRANK_VAULT_TOKEN.get_secret_value() == "CHANGEME":
        raise ValueError("OPENRANK_VAULT_TOKEN must be configured")

    try:
        client = hvac.Client(
            url=settings.OPENRANK_VAULT_URL,
            token=settings.OPENRANK_VAULT_TOKEN.get_secret_value(),
        )

        if not client.is_authenticated():
            raise ValueError("Failed to authenticate with vault - check token and URL")

        response = client.secrets.kv.v2.read_secret_version(
            path=settings.OPENRANK_VAULT_SECRET_PATH
        )

        if "data" not in response or "data" not in response["data"]:
            raise ValueError("Invalid vault response structure")

        mnemonic = response["data"]["data"].get("mnemonic")
        if not mnemonic:
            raise ValueError("Mnemonic not found in vault secret")

        return mnemonic

    except VaultError as e:
        raise ValueError(f"Vault error: {e}")
    except Exception as e:
        raise ValueError(f"Failed to fetch mnemonic from vault: {e}")


def download_results(req_id: str, out_file: Path):
    new_env = os.environ.copy()
    new_env["MNEMONIC"] = settings.get_openrank_mnemonic()
    new_env["OPENRANK_MANAGER_ADDRESS"] = settings.OPENRANK_MANAGER_ADDRESS
    new_env["CHAIN_RPC_URL"] = settings.OPENRANK_CHAIN_RPC_URL
    new_env["AWS_ACCESS_KEY_ID"] = settings.OPENRANK_AWS_ACCESS_KEY_ID
    new_env["AWS_SECRET_ACCESS_KEY"] = settings.OPENRANK_AWS_SECRET_ACCESS_KEY

    get_cmd = subprocess.run(
        ["openrank-sdk", "meta-download-results", str(req_id), str(out_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=settings.OPENRANK_TIMEOUT_SECS,
        env=new_env,
        check=True,
    )
    if get_cmd.returncode != 0:
        logger.error(f"OpenRank get-results failed for {req_id}: {get_cmd.stderr}")
        raise Exception("OpenRank get-results failed")
    logger.info(f"OpenRank get-results for {req_id} downloaded to: {out_file}")


def update_and_compute(lt_file: Path, pt_file: Path) -> str:
    new_env = os.environ.copy()
    new_env["MNEMONIC"] = settings.get_openrank_mnemonic()
    new_env["OPENRANK_MANAGER_ADDRESS"] = settings.OPENRANK_MANAGER_ADDRESS
    new_env["CHAIN_RPC_URL"] = settings.OPENRANK_CHAIN_RPC_URL
    new_env["AWS_ACCESS_KEY_ID"] = settings.OPENRANK_AWS_ACCESS_KEY_ID
    new_env["AWS_SECRET_ACCESS_KEY"] = settings.OPENRANK_AWS_SECRET_ACCESS_KEY

    compute_cmd = subprocess.run(
        [
            "openrank-sdk",
            "meta-compute-request",
            str(lt_file),
            str(pt_file),
            "--watch",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=settings.OPENRANK_TIMEOUT_SECS,
        env=new_env,
    )
    logger.info(f"OpenRank compute output: {compute_cmd}")
    if compute_cmd.returncode != 0:
        logger.error(f"OpenRank compute failed: {compute_cmd.stdout}")
        raise Exception("OpenRank compute failed")
    req_id = compute_cmd.stdout.strip()
    logger.info(f"OpenRank request id: {req_id}")
    return req_id

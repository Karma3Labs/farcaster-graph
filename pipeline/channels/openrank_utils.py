import os
import subprocess
from pathlib import Path

import hvac
from hvac.exceptions import VaultError
from loguru import logger

from config import OpenRankSettings


def get_openrank_mnemonic(openrank_settings: OpenRankSettings) -> str:
    """
    Fetch the OpenRank mnemonic from vault dynamically.
    The private key is never stored in persistent storage and is fetched fresh each time.

    Returns:
        str: The mnemonic phrase from vault

    Raises:
        RuntimeError: If vault authentication fails or secret cannot be retrieved
    """
    try:
        client = hvac.Client(
            url=openrank_settings.VAULT_URL,
            token=openrank_settings.VAULT_TOKEN.get_secret_value(),
        )

        if not client.is_authenticated():
            raise RuntimeError(
                "Failed to authenticate with vault - check token and URL"
            )

        response = client.secrets.kv.v2.read_secret_version(
            path=openrank_settings.VAULT_SECRET_PATH
        )

        return response["data"]["data"]["mnemonic"]
    except KeyError as e:
        raise RuntimeError("Mnemonic not found") from e
    except VaultError as e:
        raise RuntimeError("Vault error") from e
    except Exception as e:
        raise RuntimeError("Failed to fetch mnemonic from vault") from e


def download_results(openrank_settings: OpenRankSettings, req_id: str, out_file: Path):
    new_env = os.environ.copy()
    new_env["MNEMONIC"] = get_openrank_mnemonic(openrank_settings)
    new_env["OPENRANK_MANAGER_ADDRESS"] = openrank_settings.MANAGER_ADDRESS
    new_env["CHAIN_RPC_URL"] = openrank_settings.CHAIN_RPC_URL
    new_env["AWS_ACCESS_KEY_ID"] = openrank_settings.AWS_ACCESS_KEY_ID
    new_env["AWS_SECRET_ACCESS_KEY"] = openrank_settings.AWS_SECRET_ACCESS_KEY

    get_cmd = subprocess.run(
        ["openrank-sdk", "meta-download-results", str(req_id), str(out_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=openrank_settings.TIMEOUT_SECS,
        env=new_env,
        check=True,
    )
    if get_cmd.returncode != 0:
        logger.error(f"OpenRank get-results failed for {req_id}: {get_cmd.stderr}")
        raise Exception("OpenRank get-results failed")
    logger.info(f"OpenRank get-results for {req_id} downloaded to: {out_file}")


def update_and_compute(
    openrank_settings: OpenRankSettings, lt_file: Path, pt_file: Path
) -> str:
    new_env = os.environ.copy()
    new_env["MNEMONIC"] = get_openrank_mnemonic(openrank_settings)
    new_env["OPENRANK_MANAGER_ADDRESS"] = openrank_settings.MANAGER_ADDRESS
    new_env["CHAIN_RPC_URL"] = openrank_settings.CHAIN_RPC_URL
    new_env["AWS_ACCESS_KEY_ID"] = openrank_settings.AWS_ACCESS_KEY_ID
    new_env["AWS_SECRET_ACCESS_KEY"] = openrank_settings.AWS_SECRET_ACCESS_KEY

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
        timeout=openrank_settings.TIMEOUT_SECS,
        env=new_env,
    )
    logger.info(f"OpenRank compute output: {compute_cmd}")
    if compute_cmd.returncode != 0:
        logger.error(f"OpenRank compute failed: {compute_cmd.stdout}")
        raise Exception("OpenRank compute failed")
    req_id = compute_cmd.stdout.strip()
    logger.info(f"OpenRank request id: {req_id}")
    return req_id

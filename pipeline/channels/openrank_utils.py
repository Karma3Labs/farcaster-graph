from pathlib import Path
import subprocess
import os
import tempfile

from config import settings

from loguru import logger

def download_results(req_id: str, toml_file: Path, out_dir:Path, out_file: Path):
    new_env = os.environ.copy()
    new_env['SECRET_KEY'] = settings.OPENRANK_REQ_SECRET_KEY.get_secret_value()
    with tempfile.NamedTemporaryFile(dir=out_dir, delete=True) as temp_file:
        get_cmd = subprocess.run(
            ["openrank-sdk", "get-results", str(req_id), str(toml_file)],
            stdout=temp_file,
            stderr=subprocess.PIPE,
            text=True,
            timeout=settings.OPENRANK_TIMEOUT_SECS,
            env=new_env,
            check=True,
        )
        if get_cmd.returncode != 0:   
            logger.error(f"OpenRank get-results failed for {req_id}: {get_cmd.stderr}")
            raise Exception("OpenRank get-results failed")
        if os.path.exists(out_file):
            os.remove(out_file)
        os.link(temp_file.name, out_file) # hard link because temp file will get deleted
        logger.info(f"OpenRank get-results for {req_id} downloaded to: {out_file}")

def update_and_compute(lt_file: Path, pt_file: Path, toml_file: Path) -> str:
    new_env = os.environ.copy()
    new_env['SECRET_KEY'] = settings.OPENRANK_REQ_SECRET_KEY.get_secret_value()

    lt_cmd = subprocess.run(
        ["openrank-sdk", "trust-update", str(lt_file), str(toml_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        # check=True, # we don't want to throw error until we have a chance to print the output
        timeout=settings.OPENRANK_TIMEOUT_SECS,
        env=new_env,
    )
    logger.info(f"OpenRank trust-update output: {lt_cmd}")
    if lt_cmd.returncode != 0:
        logger.error(f"OpenRank trust-update failed: {lt_cmd.stdout}")
        raise Exception("OpenRank trust-update failed")
    pt_cmd = subprocess.run(
        ["openrank-sdk", "seed-update", str(pt_file), str(toml_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=settings.OPENRANK_TIMEOUT_SECS,
        env=new_env,
    )
    logger.info(f"OpenRank seed-update output: {pt_cmd}")
    if pt_cmd.returncode != 0:
        logger.error(f"OpenRank seed-update failed: {pt_cmd.stdout}")
        raise Exception("OpenRank seed-update failed")
    compute_cmd = subprocess.run(
        ["openrank-sdk", "compute-request", str(toml_file)],
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

import os

from config import settings

from loguru import logger

def download_results(req_id: str, out_file: Path):
    new_env = os.environ.copy()
    new_env["SECRET_KEY"] = settings.OPENRANK_REQ_SECRET_KEY.get_secret_value()
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
    new_env["SECRET_KEY"] = settings.OPENRANK_REQ_SECRET_KEY.get_secret_value()

    compute_cmd = subprocess.run(
        ["openrank-sdk", "meta-compute-request", str(lt_file), str(pt_file), "--watch"],
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

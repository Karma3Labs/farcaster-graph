# standard dependencies
import sys
import argparse
from pathlib import Path
import random
import urllib.parse

# local dependencies
from config import settings
from channels import channel_utils
import utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
from urllib3.util import Retry
import niquests
from sqlalchemy import create_engine
from sqlalchemy import text

# Configure logger
logger.remove()
level_per_module = {
    "": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout,
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=level_per_module,
           level=0)

load_dotenv()

def compare_dataframes(df1, df2):
    df1 = df1.drop(['fname', 'username', 'bal_update_ts'], axis=1).sort_values('fid').reset_index()
    logger.info(utils.df_info_to_string(df1, with_sample=True))

    df2 = df2.drop(['fname','username', 'bal_update_ts'], axis=1).sort_values('fid').reset_index()
    logger.info(utils.df_info_to_string(df2, with_sample=True))

    print(df1.compare(df2, result_names=('src', 'tgt'), align_axis=0))

    # cmp_df = df1.compare(df2, result_names=('src', 'tgt'))
    # logger.info(utils.df_info_to_string(cmp_df, with_sample=True))

def compare_urls(source_url, target_url):
    assert source_url.netloc != target_url.netloc
    assert source_url.path == target_url.path
    assert source_url.params == target_url.params
    assert source_url.query == target_url.query
    assert source_url.fragment == target_url.fragment

def main(source_url, target_url):
    logger.info(f"Comparing source and target: {source_url} and {target_url}")
    compare_urls(source_url, target_url)

    logger.info("Fetching data from source and target")
    src_json = niquests.get(
        source_url.geturl(), 
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=5,
    )
    tgt_json = niquests.get(
        target_url.geturl(), 
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=5,
    )

    logger.info("Source response:")
    src_df = pd.DataFrame(src_json.json()['result'])
    logger.info(utils.df_info_to_string(src_df, with_sample=True))

    logger.info("Target response:")
    tgt_df = pd.DataFrame(tgt_json.json()['result'])
    logger.info(utils.df_info_to_string(tgt_df, with_sample=True))

    compare_dataframes(src_df, tgt_df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s",
        "--source",
        type=lambda f: urllib.parse.urlparse(f),
        help="source url",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--target",
        type=lambda f: urllib.parse.urlparse(f),
        help="target url",
        required=True,
    )
    args = parser.parse_args()
    print(args)
    logger.info(settings)

    main(args.source, args.target)
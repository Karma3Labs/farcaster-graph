import datetime
import io
import logging
import logging.handlers
import os
import sys
from enum import Enum
from pathlib import Path

import pandas as pd
import psutil
import pytz

from config import settings


class DOW(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


def df_info_to_string(df: pd.DataFrame, with_sample: bool = False, head: bool = False):
    buf = io.StringIO()
    df.info(verbose=True, buf=buf, memory_usage="deep", show_counts=True)
    if with_sample and len(df) > 0:
        if head:
            buf.write(f"{'-' * 15}\n| Head:\n{'-' * 15}\n")
            df.head().to_csv(buf, index=False)
        else:
            buf.write(f"{'-' * 15}\n| Sample rows:\n{'-' * 15}\n")
            df.sample(min(10, len(df) - 1)).to_csv(buf, index=False)
    return buf.getvalue()


def log_memusage(logger: logging.Logger, prefix: str = ""):
    mem_usage = psutil.virtual_memory()
    logger.info(f"{prefix}Total: {mem_usage.total / (1024**2):.2f}M")
    logger.info(f"{prefix}PctUsed: {mem_usage.percent}%")
    logger.info(f"{prefix}Available: {mem_usage.available / (1024**2):.2f}M")
    logger.info(f"{prefix}Free: {mem_usage.free / (1024**2):.2f}M")


def setup_console_logger(logger):
    # create a console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    # create a logging format
    formatter = logging.Formatter(settings.LOG_FORMAT)
    ch.setFormatter(formatter)
    # add the handler to the logger
    logger.addHandler(ch)


def setup_filelogger(logger, script_path):
    # create a file handler
    filename = f"{Path(script_path).expanduser().resolve().stem}.log"
    filepath = Path(settings.LOG_PATH) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(str(filepath))
    # fh = logging.handlers.RotatingFileHandler('/var/log/app/myfeed/%s.log' % programname)
    fh.setLevel(logging.INFO)
    # create a logging format
    formatter = logging.Formatter(settings.LOG_FORMAT)
    fh.setFormatter(formatter)
    # add the handler to the logger
    logger.addHandler(fh)


def gen_datetime_filepath(prefix, ext, basedir="/tmp/onchain-output"):
    fdatetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{fdatetime}.{ext}"
    return os.path.join(basedir, filename)


def pacific_9am_in_utc_time(date_str: str = None):
    # TODO move this to utils
    pacific_tz = pytz.timezone("US/Pacific")
    if date_str:
        pacific_9am_str = " ".join([date_str, "09:00:00"])
    else:
        pacific_9am_str = " ".join(
            [datetime.datetime.now(pacific_tz).strftime("%Y-%m-%d"), "09:00:00"]
        )
    pacific_time = pacific_tz.localize(
        datetime.datetime.strptime(pacific_9am_str, "%Y-%m-%d %H:%M:%S")
    )
    utc_time = pacific_time.astimezone(pytz.utc)
    return utc_time


def dow_utc_time(dow: DOW):
    utc_time = pacific_9am_in_utc_time()
    return utc_time - datetime.timedelta(days=utc_time.weekday() - dow.value)


def last_dow_utc_time(dow: DOW):
    utc_time = pacific_9am_in_utc_time()
    return utc_time - datetime.timedelta(days=utc_time.weekday() - dow.value + 7)

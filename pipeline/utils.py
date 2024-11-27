import logging
import logging.handlers
import sys
import io
import datetime
import os
from pathlib import Path

from config import settings

import psutil
import pandas as pd

def df_info_to_string(df: pd.DataFrame, with_sample:bool = False, head:bool = False):
  buf = io.StringIO()
  df.info(verbose=True, buf=buf, memory_usage="deep", show_counts=True)
  if with_sample and len(df) > 0:
    if head:
      buf.write(f"{'-' *15}\n| Head:\n{'-' *15}\n")
      df.head().to_csv(buf, index=False)
    else:
      buf.write(f"{'-' *15}\n| Sample rows:\n{'-' *15}\n")
      df.sample(min(10, len(df)-1)).to_csv(buf, index=False)
  return buf.getvalue()

def log_memusage(logger:logging.Logger, prefix: str = ''):
  mem_usage = psutil.virtual_memory()
  logger.info(f"{prefix}Total: {mem_usage.total/(1024**2):.2f}M")
  logger.info(f"{prefix}PctUsed: {mem_usage.percent}%")
  logger.info(f"{prefix}Available: {mem_usage.available/(1024**2):.2f}M")
  logger.info(f"{prefix}Free: {mem_usage.free/(1024**2):.2f}M" )

def setup_consolelogger(logger):
  # create a console handler
  ch = logging.StreamHandler(sys.stdout)
  ch.setLevel(logging.DEBUG)
  # create a logging format
  formatter = logging.Formatter(settings.LOG_FORMAT)
  ch.setFormatter(formatter)
  # add the handler to the logger
  logger.addHandler(ch)

def setup_filelogger(logger, scriptpath):
  # create a file handler
  logfilename = f"{Path(scriptpath).expanduser().resolve().stem}.log"
  logfilepath = Path(settings.LOG_PATH) / logfilename
  logfilepath.parent.mkdir(parents=True, exist_ok=True)
  fh = logging.handlers.RotatingFileHandler(str(logfilepath))
  # fh = logging.handlers.RotatingFileHandler('/var/log/app/myfeed/%s.log' % programname)
  fh.setLevel(logging.INFO)
  # create a logging format
  formatter = logging.Formatter(settings.LOG_FORMAT)
  fh.setFormatter(formatter)
  # add the handler to the logger
  logger.addHandler(fh)

def gen_datetime_filepath(prefix, ext, basedir='/tmp/onchain-output'):
  fdatetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  filename = f"{prefix}_{fdatetime}.{ext}"
  return os.path.join(basedir, filename)

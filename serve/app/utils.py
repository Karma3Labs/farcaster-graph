import io

from loguru import logger
import psutil
import pandas as pd

def log_memusage(logger:logger):
  mem_usage = psutil.virtual_memory()
  logger.info(f"Total: {mem_usage.total/(1024**2):.2f}M")
  logger.info(f"Used: {mem_usage.percent}%")
  logger.info(f"Used: {mem_usage.used/(1024**2):.2f}M")
  logger.info(f"Free: {mem_usage.free/(1024**2):.2f}M" )

def df_info_to_string(df: pd.DataFrame, with_sample:bool = False):
  buf = io.StringIO()
  df.info(verbose=True, buf=buf, memory_usage="deep", show_counts=True)
  if with_sample:
    buf.write(f"{'-' *15}\n| Sample rows:\n{'-' *15}\n")
    df.sample(5).to_csv(buf, index=False)
  return buf.getvalue()
from loguru import logger
import psutil

def log_memusage(logger:logger):
  mem_usage = psutil.virtual_memory()
  logger.info(f"Total: {mem_usage.total/(1024**2):.2f}M")
  logger.info(f"Used: {mem_usage.percent}%")
  logger.info(f"Used: {mem_usage.used/(1024**2):.2f}M")
  logger.info(f"Free: {mem_usage.free/(1024**2):.2f}M" )
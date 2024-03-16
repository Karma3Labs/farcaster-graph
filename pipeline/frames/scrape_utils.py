import logging
from enum import Enum

from timer import Timer

from bs4 import BeautifulSoup
import requests

class URLCategory(Enum):
  FRAME = 'frame'
  TIMEOUT = 'timeout'
  BAD = 'bad'
  UNKNOWN = 'unknown'

async def categorize_url(logger: logging.Logger, url_id: int, url:str, timeout: int) -> URLCategory:
  logger.debug(f"Fetching {url_id} - {url}")
  try:
    response = requests.get(url, timeout=timeout)
  except requests.Timeout as e:
    logger.error(f"{url} timed out: {e}")
    return (url_id, URLCategory.TIMEOUT.value)
  except requests.exceptions.RequestException as e:
    logger.error(f"bad url {url}: {e}")
    return (url_id, URLCategory.BAD.value)
  soup = BeautifulSoup(response.content, 'html.parser')
  frame_meta = soup.find('meta', attrs={"property":"fc:frame"})
  return (url_id, URLCategory.FRAME.value) if frame_meta \
          else (url_id, URLCategory.UNKNOWN.value)

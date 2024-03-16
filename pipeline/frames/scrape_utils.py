import logging
from enum import Enum
import asyncio

from bs4 import BeautifulSoup
import aiohttp as aiohttp

class URLCategory(Enum):
  FRAME = 'frame'
  TIMEOUT = 'timeout'
  BAD = 'bad'
  UNKNOWN = 'unknown'
  ERROR = 'error'

async def categorize_url(logger: logging.Logger, url_id: int, url:str, session: aiohttp.ClientSession) -> URLCategory:
  logger.debug(f"Fetching {url_id} - {url}")
  try:
    async with session.get(url) as resp:
      body = await resp.text()
      soup = BeautifulSoup(body, 'html.parser')
      frame_meta = soup.find('meta', attrs={"property":"fc:frame"})
      return (url_id, URLCategory.FRAME.value) if frame_meta \
                  else (url_id, URLCategory.UNKNOWN.value)
  except asyncio.TimeoutError as e:
    logger.error(f"{url_id} - {url} timed out: {e}")
    return (url_id, URLCategory.TIMEOUT.value)
  except aiohttp.InvalidURL as e:
    logger.error(f"bad url {url_id} - {url}: {e}")
    return (url_id, URLCategory.BAD.value)
  except aiohttp.ClientError as e:
    logger.error(f"error {url_id} - {url}: {e}")
    return (url_id, URLCategory.ERROR.value)
  except Exception as e:
    logger.error(f"error {url_id} - {url}: {e}")
    return (url_id, URLCategory.ERROR.value)
  
# async def categorize_url(logger: logging.Logger, url_id: int, url:str, timeout: aiohttp.ClientTimeout) -> URLCategory:
#   logger.debug(f"Fetching {url_id} - {url}")
#   async with aiohttp.ClientSession(timeout=timeout) as session:
#     try:
#       async with session.get(url) as resp:
#         body = await resp.text()
#         soup = BeautifulSoup(body, 'html.parser')
#         frame_meta = soup.find('meta', attrs={"property":"fc:frame"})
#         return (url_id, URLCategory.FRAME.value) if frame_meta \
#                     else (url_id, URLCategory.UNKNOWN.value)
#     except asyncio.TimeoutError as e:
#       logger.error(f"{url_id} - {url} timed out: {e}")
#       return (url_id, URLCategory.TIMEOUT.value)
#     except aiohttp.InvalidURL as e:
#       logger.error(f"bad url {url_id} - {url}: {e}")
#       return (url_id, URLCategory.BAD.value)
#     except aiohttp.ClientError as e:
#       logger.error(f"error {url_id} - {url}: {e}")
#       return (url_id, URLCategory.ERROR.value)

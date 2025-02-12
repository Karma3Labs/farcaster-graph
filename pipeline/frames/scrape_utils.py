import logging
from enum import Enum
from typing import NamedTuple
import asyncio
from urllib.parse import urlparse

import tldextract
from bs4 import BeautifulSoup
import aiohttp as aiohttp

class URLCategory(Enum):
  FRAME = 'frame'
  TIMEOUT = 'timeout'
  BAD = 'bad'
  UNKNOWN = 'unknown'
  ERROR = 'error'

async def categorize_url(
    logger: logging.Logger,
    url_id: int, url:str,
    session: aiohttp.ClientSession,
    timeout: aiohttp.ClientTimeout
) -> tuple[int, str]:
  logger.debug(f"Fetching {url_id} - {url}")
  if urlparse(url).scheme not in ['http','https']:
    logger.error(f"bad url {url_id} - {url}")
    return (url_id, URLCategory.BAD.value)

  try:
    async with session.get(url, timeout=timeout) as resp:
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

class URL_parts(NamedTuple):
  url_id: int
  scheme: str
  domain: str
  subdomain: str
  tld: str
  path: str

def parse_url(
    logger: logging.Logger,
    url_id: int,
    url:str
) -> tuple[int, str, str, str, str, str]:
  logger.debug(f"parsing {url_id} - {url}")
  try:
    parse_result = urlparse(url)
    extract = tldextract.extract(url)
    path = parse_result.path
    if path.endswith(':'):
      path = path[:-1]
    return tuple(URL_parts(url_id,
                    parse_result.scheme,
                    extract.domain,
                    extract.subdomain,
                    extract.suffix,
                    path))
  except Exception as e:
    logger.error(f"error {url_id} - {url}: {e}")
    return (url_id, '', '', '', '', '')
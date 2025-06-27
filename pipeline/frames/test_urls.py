# standard dependencies
import sys

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

# local dependencies
from config import settings

from . import scrape_utils

logger.remove()
level_per_module = {"": settings.LOG_LEVEL, "silentlib": False}
logger.add(
    sys.stdout,
    colorize=True,
    format=settings.LOGURU_FORMAT,
    filter=level_per_module,
    level=0,
)


def test():
    url = "https://apis.cast.k3l.io"
    url_category = scrape_utils.categorize_url(logger, -1, url, timeout=1)
    logger.debug(f"{url} category ? {url_category}")

    url = "https://cast.k3l.io/apis123"
    url_category = scrape_utils.categorize_url(logger, -1, url, timeout=1)
    logger.debug(f"{url} category ? {url_category}")

    url = "https://cast.k3l.io"
    url_category = scrape_utils.categorize_url(logger, -1, url, timeout=1)
    logger.debug(f"{url} category ? {url_category}")

    url = "https://dune-frames.vercel.app/api"
    url_category = scrape_utils.categorize_url(
        logger, -1, url, settings.FRAMES_SCRAPE_TIMEOUT_SECS
    )
    logger.debug(f"{url} category ? {url_category}")

    url = "https://www.youtube.com"
    url_category = scrape_utils.categorize_url(
        logger, -1, url, settings.FRAMES_SCRAPE_TIMEOUT_SECS
    )
    logger.debug(f"{url} category ? {url_category}")

    url = "https://www.youttube.com"
    url_category = scrape_utils.categorize_url(
        logger, -1, url, settings.FRAMES_SCRAPE_TIMEOUT_SECS
    )
    logger.debug(f"{url} category ? {url_category}")

    url = "abc"
    url_category = scrape_utils.categorize_url(
        logger, -1, url, settings.FRAMES_SCRAPE_TIMEOUT_SECS
    )
    logger.debug(f"{url} category ? {url_category}")

    url = "http://1"
    url_category = scrape_utils.categorize_url(
        logger, -1, url, settings.FRAMES_SCRAPE_TIMEOUT_SECS
    )
    logger.debug(f"{url} category ? {url_category}")


if __name__ == "__main__":
    load_dotenv()
    print(settings)

    logger.debug("####### TODO use pytest ########")
    test()

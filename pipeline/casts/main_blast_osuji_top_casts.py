# standard dependencies
import sys
import niquests

from config import settings
from . import cast_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger

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

def main():
    pg_dsn = settings.ALT_POSTGRES_DSN.get_secret_value()
    df = cast_db_utils.fetch_osuji_top_casts_df(logger, pg_dsn).head(10)
    message = "These are @osuji.eth's top casts 🚀:\n" + "\n".join([
        f"{i + 1} - {row['url']}" for i, row in df.iterrows()
    ])
    logger.info(message)
    response = niquests.post(
        "https://top-erc20-tokens.vercel.app/api",
        headers={"Content-Type": "application/json"},
        json={"message": message},
        timeout = 30,
        allow_redirects=False
    )
    response.raise_for_status()

    logger.info("Osuji.eth's top casts successfully blasted")



if __name__ == "__main__":
    load_dotenv()
    logger.info(settings)
    logger.info("starting to blast all Osuji.eth's top casts")
    main()

# standard dependencies
import sys
from datetime import date

# local dependencies
from config import settings
import utils
from . import cast_db_utils

# 3rd party dependencies
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine

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
    df = cast_db_utils.fetch_top_casters_df(logger, pg_dsn)
    # top_casters = []
    # for caster in casters:
    #     top_casters.append({'i': caster['i'], 'v': caster['v']})

    # df = pd.DataFrame(data=top_casters)
    df["date_iso"] = date.today()
    logger.info(utils.df_info_to_string(df, with_sample=True))

    postgres_engine = create_engine(
        settings.ALT_POSTGRES_URL.get_secret_value(),
        connect_args={"connect_timeout": settings.POSTGRES_TIMEOUT_SECS * 1_000},
    )
    logger.info(postgres_engine)
    with postgres_engine.connect() as connection:
        df.to_sql('k3l_top_casters', con=connection, if_exists='append', index=False)

    # cast_db_utils.insert_dune_table(settings.DUNE_API_KEY, 'openrank', 'top_caster', df)

    logger.info('top casters data updated to DB')

    # end while loop


if __name__ == "__main__":
    load_dotenv()
    print(settings)

    # parser = argparse.ArgumentParser(description='Fetch top casters, persist the dataframe to db')
    #
    # parser.add_argument('-u', '--user')
    # parser.add_argument('-p', '--password')
    # parser.add_argument('-e', '--endpoint')
    #
    # args = parser.parse_args()

    logger.info('hello hello')
    main()

# standard dependencies
import sys
from datetime import datetime, timedelta, date

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
    pg_dsn = settings.POSTGRES_DSN.get_secret_value()

    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)

    df = cast_db_utils.fetch_top_spammers_df(
        logger, pg_dsn, start_date=thirty_days_ago, end_date=now
    )
    df["date_iso"] = date.today()
    logger.info(utils.df_info_to_string(df, with_sample=True))
    type_dict = {
        "fid": int,
        "display_name": str,
        "total_outgoing": int,
        "spammer_score": float,
        "total_parent_casts": int,
        "total_replies_with_parent_hash": int,
        "global_openrank_score": float,
        "global_rank": int,
        "total_global_rank_rows": int,
        "date_iso": str,
    }
    df = df.astype(type_dict, errors="ignore")
    df["display_name"] = df["display_name"].fillna("")
    df = df.fillna(0)
    logger.info(utils.df_info_to_string(df, with_sample=True))

    # top_spammers = []
    # for s in rows:
    #   logger.info(s)
    #   row = {
    #     'fid': s['fid'],
    #     'display_name': str(s['display_name']),
    #     'total_outgoing': int(s['total_outgoing']),
    #     'spammer_score': float(s['spammer_score']) if s['spammer_score'] else 0.0,
    #     'total_parent_casts': int(s['total_parent_casts']),
    #     'total_replies_with_parent_hash': int(s['total_replies_with_parent_hash']),
    #     'global_openrank_score': float(s['global_openrank_score']) if s['global_openrank_score'] else 0.0,
    #     'global_rank': int(s['global_rank']) if s['global_rank'] else 0,
    #     'total_global_rank_rows': int(s['total_global_rank_rows']) if s['total_global_rank_rows'] else 0,
    #   }
    #   top_spammers.append(row)
    # df = pd.DataFrame(top_spammers)
    # df["date_iso"] = date.today()
    # logger.info(df.head())

    postgres_engine = create_engine(settings.POSTGRES_URL.get_secret_value(), connect_args={"connect_timeout": settings.POSTGRES_TIMEOUT_SECS * 1_000})
    logger.info(postgres_engine)
    with postgres_engine.connect() as connection:
        df.to_sql('k3l_top_spammers', con=connection, if_exists='append', index=False)

    logger.info("top spammers data updated to DB")


if __name__ == "__main__":
  load_dotenv()
  print(settings)
  logger.info('hello hello')
  main()
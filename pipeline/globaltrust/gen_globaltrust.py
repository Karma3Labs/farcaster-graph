# standard dependencies
import logging

# local dependencies
import utils
from . import db_utils
from . import go_eigentrust
from config import settings
from timer import Timer
from .queries import IJVSql, IVSql

# 3rd party dependencies
from dotenv import load_dotenv
import pandas as pd



def fetch_interactions_df(pg_dsn: str) -> pd.DataFrame:
  df = db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.LIKES)
  utils.log_memusage(logger)

  with Timer(name="merge_replies"):
    df = df.merge(db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.REPLIES), 
                  how='outer', 
                  left_on=['i','j'], right_on=['i','j'], 
                  indicator=False)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="merge_mentions"):
    df = df.merge(db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.MENTIONS), 
                  how='outer', 
                  left_on=['i','j'], right_on=['i','j'], 
                  indicator=False)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="merge_recasts"):
    df = df.merge(db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.RECASTS), 
                  how='outer', 
                  left_on=['i','j'], right_on=['i','j'], 
                  indicator=False)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="merge_follows"):
    df = df.merge(db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IJVSql.FOLLOWS), 
                  how='outer', 
                  left_on=['i','j'], right_on=['i','j'], 
                  indicator=False)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  return df  



def main(pg_dsn: str):
  utils.log_memusage(logger)
  df = fetch_interactions_df(pg_dsn)

  with Timer(name="l1rep1rec1m1"):
    df['l1rep1rec1m1'] = df.loc[:,['likes_v', 
                                  'replies_v', 
                                  'mentions_v', 
                                  'reacts_v', 
                                  'follows_v']].sum(axis=1)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="l1rep6rec3m12"):
    df['l1rep6rec3m12'] = df['likes_v'].fillna(0) \
                          + (df['replies_v'].fillna(0) * 6.0) \
                          + (df['reacts_v'].fillna(0) * 3.0) \
                          + (df['mentions_v'].fillna(0) * 12.0) \
                          + df['follows_v'].fillna(0)
    logger.info(utils.df_info_to_string(df, with_sample=True))
  utils.log_memusage(logger)

  lt_l1rep6rec3m12enhanced_df = df[df['follows_v'].notna()][['i','j','l1rep6rec3m12']].rename(columns={'l1rep6rec3m12':'v'})
  logger.info(utils.df_info_to_string(lt_l1rep6rec3m12enhanced_df, with_sample=True))
  utils.log_memusage(logger)

  lt_follows_df = df[['i','j','follows_v']].rename(columns={'follows_v':'v'})
  logger.info(utils.df_info_to_string(lt_follows_df, with_sample=True))
  utils.log_memusage(logger)

  pt_popular_df = db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IVSql.PRETRUST_POPULAR)
  logger.info(utils.df_info_to_string(pt_popular_df, with_sample=True))
  utils.log_memusage(logger)

  pt_og_df = db_utils.ijv_df_read_sql_tmpfile(logger, pg_dsn, IVSql.PRETRUST_OG)
  logger.info(utils.df_info_to_string(pt_og_df, with_sample=True))
  utils.log_memusage(logger)

  with Timer(name="prep_eigentrust"):
    localtrust = lt_l1rep6rec3m12enhanced_df.to_dict(orient="records")  
    max_lt_id = max(lt_l1rep6rec3m12enhanced_df['i'].max(), lt_l1rep6rec3m12enhanced_df['j'].max())
    pretrust = pt_popular_df.to_dict(orient="records")
    max_pt_id = pt_popular_df['i'].max()

  globaltrust = go_eigentrust.go_eigentrust(logger, 
                                            pretrust,
                                            max_pt_id,
                                            localtrust,
                                            max_lt_id
                                            )
  
  with Timer(name="post_eigentrust"):
    gt_df = pd.DataFrame.from_records(globaltrust)
    logger.info(utils.df_info_to_string(gt_df, with_sample=True))
  utils.log_memusage(logger)

  

if __name__ == '__main__':
  load_dotenv()
  print(settings)

  logger = logging.getLogger()
  utils.setup_filelogger(logger, __file__)
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  # perf optimization to avoid copies unless there is a write on shared data
  pd.set_option("mode.copy_on_write", True)

  main(settings.POSTGRES_DSN.get_secret_value())


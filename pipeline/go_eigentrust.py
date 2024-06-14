import time

from config import settings

from loguru import logger
import pandas
import numpy as np
import requests

def get_scores(lt_df: pandas.DataFrame, pt_ids: list[int]):
  start_time = time.perf_counter()
  # TODO Perf - pt_ids should be a 'set[int]' and not a 'list[int]'
  stacked = lt_df.loc[:, ('i','j')].stack()
  pseudo_id, orig_id = stacked.factorize()

  # pseudo_df is a new dataframe to avoid modifying existing shared global df
  pseudo_df = pandas.Series(pseudo_id, index=stacked.index).unstack()
  pseudo_df.loc[:,('v')] = lt_df.loc[:,('v')]

  pt_len = len(pt_ids)
  pretrust = [{'i': orig_id.get_loc(fid), 'v': 1/pt_len} for fid in pt_ids]
  max_pt_id = len(orig_id)

  localtrust = pseudo_df.to_dict(orient="records")
  max_lt_id = len(orig_id)

  logger.info(f"max_lt_id:{max_lt_id}, localtrust size:{len(localtrust)}," \
               f" max_pt_id:{max_pt_id}, pretrust size:{len(pretrust)}")
  logger.trace(f"localtrust:{localtrust}")
  logger.trace(f"pretrust:{pretrust}")

  scores = go_eigentrust(pretrust=pretrust,
                           max_pt_id=max_pt_id,
                           localtrust=localtrust,
                           max_lt_id=max_lt_id
                           )
  logger.trace(f"scores:{scores}")

  i_scores = [ {'i': int(orig_id[score['i']]), 'v': score['v']} for score in scores]
  logger.info(f"get_scores took {time.perf_counter() - start_time} secs for {len(i_scores)} scores")
  return i_scores

def go_eigentrust(
    pretrust: list[dict],
    max_pt_id: np.int32,
    localtrust: list[dict],
    max_lt_id: np.int32,
):
  start_time = time.perf_counter()
  req = {
    "pretrust": {
      "scheme": 'inline',
      "size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
      "entries": pretrust,
    },
    "localTrust": {
      "scheme": 'inline',
      "size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
      "entries": localtrust,
    },
    "alpha": settings.EIGENTRUST_ALPHA,
    # "epsilon": settings.EIGENTRUST_EPSILON,
    # "max_iterations": settings.EIGENTRUST_MAX_ITER,
    # "flatTail": settings.EIGENTRUST_FLAT_TAIL
  }

  logger.info(f"calling go_eigentrust")
  response = requests.post(f"{settings.GO_EIGENTRUST_URL}/basic/v1/compute",
                          json=req,
                          headers = {
                              'Accept': 'application/json',
                              'Content-Type': 'application/json'
                              },
                          timeout=settings.GO_EIGENTRUST_TIMEOUT_MS)

  if response.status_code != 200:
      logger.error(f"Server error: {response.status_code}:{response.reason}")
      raise Exception(f"Server error: {response.status_code}:{response.reason}")
  trustscores = response.json()['entries']
  logger.info(f"go_eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores")
  return trustscores

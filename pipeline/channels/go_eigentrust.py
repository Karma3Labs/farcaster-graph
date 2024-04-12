import logging

from timer import Timer
from config import settings

import numpy as np
import requests


def go_eigentrust(
    logger: logging.Logger, 
    pretrust: list[dict],
    max_pt_id: np.int32,
    localtrust: list[dict],
    max_lt_id: np.int32,
):
  with Timer(name="go_eigentrust"):
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
      "epsilon": settings.EIGENTRUST_EPSILON,
      "max_iterations": settings.EIGENTRUST_MAX_ITER,
      "flatTail": settings.EIGENTRUST_FLAT_TAIL
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
  return trustscores

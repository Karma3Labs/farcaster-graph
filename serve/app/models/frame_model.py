from enum import StrEnum
from typing import NamedTuple, Self
import re

class ScoreAgg(StrEnum):
  RMS = 'rms'
  SUM_SQ = 'sumsquare'
  SUM = 'sum'

class Voting(StrEnum):
  SINGLE = 'single'
  MULTIPLE = 'multiple'
  # TODO
  # QUADRATIC = 'quadratic'

class Weights(NamedTuple):
  cast:int = 10
  recast:int = 5
  like:int = 1

  @staticmethod
  def from_str(weights_str:str) -> Self:
    wts = re.search(r'^[lL](\d{,2})[cC](\d{,2})[rR](\d{,2})$', weights_str)
    if wts is None:
      raise Exception("Invalid weights")
    return Weights(like=wts.group(1), cast=wts.group(2), recast=wts.group(3))


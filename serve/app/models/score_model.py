from enum import StrEnum
from typing import NamedTuple, Self
import re

class ScoreAgg(StrEnum):
  RMS = 'rms'
  SUMSQUARE = 'sumsquare'
  SUM = 'sum'

class Voting(StrEnum):
  SINGLE = 'single'
  MULTIPLE = 'multiple'
  # TODO
  # QUADRATIC = 'quadratic'

class Sorting_Order(StrEnum):
  POPULAR = 'popular'
  RECENT = 'recent'

class Weights(NamedTuple):
  cast:int = 10
  recast:int = 5
  reply:int = 7
  like:int = 1

  @staticmethod
  def from_str(weights_str:str) -> Self:
    wts = re.search(r'^([lL](\d{1,2}))?([cC](\d{1,2}))?([rR](\d{1,2}))?([yY](\d{1,2}))?$', weights_str)
    if wts is None:
      raise Exception("Invalid weights")
    return Weights(like=0 if wts.group(2) is None else wts.group(2), 
                   cast=0 if wts.group(4) is None else wts.group(4), 
                   recast=0 if wts.group(6) is None else wts.group(6), 
                   reply=0 if wts.group(8) is None else wts.group(8))


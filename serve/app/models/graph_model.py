from typing import NamedTuple
from enum import Enum
from datetime import datetime, timezone

import polars

class GraphType(Enum):
  following = 1
  engagement = 3

class PlGraph(NamedTuple):
  success_file: str
  df: polars.DataFrame
  mtime: float

  def __str__(self):
    return f"""
      shape: {self.df.shape}
      sample: {self.df.sample(n=min(5, len(self.df)))}
      size_mb: {self.df.estimated_size('mb')}
      flags: {self.df.flags}
      mtime: {datetime.fromtimestamp(self.mtime, tz=timezone.utc).isoformat()}
      """
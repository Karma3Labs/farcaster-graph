from typing import NamedTuple
from enum import Enum
import io

import igraph
import pandas

class GraphType(Enum):
  following = 1
#   engagement = 3
#   v3engagement = 9
  ninetydays = 5

class GraphTimeframe(str, Enum):
#   lifetime = "lifetime"
  ninetydays = "90d"

class Graph(NamedTuple):
  success_file: str
  df: pandas.DataFrame
  graph: igraph.Graph
  type: GraphType
  mtime: float

  def __str__(self):
    df_info=io.StringIO()
    self.df.info(buf=df_info)
    return f"""
      type: {self.type}
      dataframe: {df_info.getvalue()}
      igraph: {self.graph.summary()}
      mtime: {self.mtime}
      """
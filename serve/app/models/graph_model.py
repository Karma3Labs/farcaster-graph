from typing import NamedTuple
from enum import Enum
import io

import igraph
import pandas

class GraphType(Enum):
  following = 'following'
  engagement = 'engagement'

class Graph(NamedTuple):
  success_file: str
  df: pandas.DataFrame
  idx: pandas.DataFrame
  graph: igraph.Graph
  type: GraphType
  mtime: float

  def __str__(self):
    df_info=io.StringIO()
    self.df.info(buf=df_info)
    idx_info=io.StringIO()
    self.idx.info(buf=idx_info)
    return f"""
      type: {self.type}
      dataframe: {df_info.getvalue()}
      idx: {idx_info.getvalue()}
      igraph: {self.graph.summary()}
      mtime: {self.mtime}
      """
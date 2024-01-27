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
  graph: igraph.Graph
  type: GraphType
  mtime: float

  def __str__(self):
    buf=io.StringIO()
    self.df.info(buf=buf)
    return f"""
      type: {self.type}
      dataframe: {buf.getvalue()}
      igraph: {self.graph.summary()}
      mtime: {self.mtime}
      """
from typing import NamedTuple
from enum import Enum
import igraph

class GraphType(Enum):
  following = 'following'
  engagement = 'engagement'

class Graph(NamedTuple):
  graph_file: str
  graph: igraph.Graph
  type: GraphType
  mtime: float
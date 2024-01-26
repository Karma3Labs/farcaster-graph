import os
from typing import NamedTuple
import math

from . import utils 
from .config import settings
import igraph
from loguru import logger

class Graph(NamedTuple):
  graph_file: str
  graph: igraph.Graph
  mtime: float


class GraphLoader:

  def __init__(self) -> None:
    self.graphs = self.load_graphs()

  def get_graphs(self):
    return self.graphs

  def load_graph(self, graph_file):
    logger.info(f"loading {graph_file}")
    g = igraph.Graph.Read_Pickle(str(graph_file))
    utils.log_memusage(logger)
    return Graph(
      graph_file = graph_file,
      graph = g,
      mtime = os.path.getmtime(graph_file)
    )

  def load_graphs(self) -> dict:
    # TODO use TypedDict or a pydantic model
    graphs = {}

    # TODO fix hardcoding of name -> file, type of model
    graphs['following'] = self.load_graph(settings.FOLLOW_GRAPH)
    logger.info(f"loaded {graphs['following']}")

    graphs['engagement'] = self.load_graph(settings.ENGAGEMENT_GRAPH)
    logger.info(f"loaded {graphs['engagement']}")

    return graphs


  def reload_if_required(self):
    logger.info("checking graphs mtime")
    try:
      for _, model in self.graphs.items():
        is_graph_modified = not math.isclose(model.mtime, os.path.getmtime(model.graph_file), rel_tol=1e-9)
        logger.debug(f"In-memory mtime {model.mtime}, OS mtime {os.path.getmtime(model.graph_file)} {"are not close" if is_graph_modified else "are close"}")
        if is_graph_modified:
          logger.info("reload graphs")
          self.graphs = self.load_graphs()
          break
    except Exception as e:
      logger.error(e)
    except:
      logger.error("something bad happened")
    return

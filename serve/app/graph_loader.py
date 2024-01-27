import os
import math

from . import utils 
from .config import settings
from .models.graph_model import Graph, GraphType

import igraph
from loguru import logger


class GraphLoader:

  def __init__(self) -> None:
    self.graphs = self.load_graphs()

  def get_graphs(self):
    return self.graphs

  def load_graph(self, graph_file, graph_type: GraphType):
    logger.info(f"loading {graph_file}")
    g = igraph.Graph.Read_Pickle(str(graph_file))
    utils.log_memusage(logger)
    return Graph(
      graph_file = graph_file,
      graph = g,
      type = graph_type,
      mtime = os.path.getmtime(graph_file)
    )

  def load_graphs(self) -> dict:
    # TODO use TypedDict or a pydantic model
    graphs = {}

    # TODO fix hardcoding of name -> file, type of model
    graphs[GraphType.following] = self.load_graph(settings.FOLLOW_GRAPH, GraphType.following)
    logger.info(f"loaded {graphs[GraphType.following]}")
    logger.info(graphs[GraphType.following].graph.summary())

    graphs[GraphType.engagement] = self.load_graph(settings.ENGAGEMENT_GRAPH, GraphType.engagement)
    logger.info(f"loaded {graphs[GraphType.engagement]}")
    logger.info(graphs[GraphType.engagement].graph.summary())

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

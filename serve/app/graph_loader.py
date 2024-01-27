import os
import math

from . import utils 
from .config import settings
from .models.graph_model import Graph, GraphType

import igraph
import pandas
from loguru import logger

class GraphLoader:

  def __init__(self) -> None:
    self.graphs = self.load_graphs()

  def get_graphs(self):
    return self.graphs

  def load_graph(self, path_prefix, graph_type: GraphType):
    sfile = f"{path_prefix}_SUCCESS"
    dfile = f"{path_prefix}_df.pkl"
    utils.log_memusage(logger)
    logger.info(f"loading {dfile}")
    df = pandas.read_pickle(dfile)
    gfile = f"{path_prefix}_ig.pkl"
    logger.info(f"loading {gfile}")
    g = igraph.Graph.Read_Pickle(gfile)
    utils.log_memusage(logger)
    return Graph(
      success_file=sfile,
      df=df,
      graph=g,
      type=graph_type,
      mtime=os.path.getmtime(sfile),
    )

  def load_graphs(self) -> dict:
    # TODO use TypedDict or a pydantic model
    graphs = {}

    # TODO fix hardcoding of name -> file, type of model
    graphs[GraphType.following] = self.load_graph(settings.FOLLOW_GRAPH_PATHPREFIX, GraphType.following)
    logger.info(f"loaded {graphs[GraphType.following]}")
    logger.info(graphs[GraphType.following].graph.summary())

    graphs[GraphType.engagement] = self.load_graph(settings.ENGAGEMENT_GRAPH_PATHPREFIX, GraphType.engagement)
    logger.info(f"loaded {graphs[GraphType.engagement]}")

    return graphs


  def reload_if_required(self):
    logger.info("checking graphs mtime")
    try:
      for _, model in self.graphs.items():
        is_graph_modified = not math.isclose(model.mtime, os.path.getmtime(model.success_file), rel_tol=1e-9)
        logger.debug(
                      f"In-memory mtime {model.mtime},"
                      f" OS mtime {os.path.getmtime(model.success_file)}"
                      f" {"are not close" if is_graph_modified else "are close"}"
                    )
        if is_graph_modified:
          logger.info("reload graphs")
          self.graphs = self.load_graphs()
          break
    except Exception as e:
      logger.error(e)
    except:
      logger.error("something bad happened")
    return

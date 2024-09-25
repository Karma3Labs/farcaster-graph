import os
import math
import time

from . import utils, main
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
    logger.info(f"unpickling {dfile}")
    df = pandas.read_pickle(dfile)
    logger.info(utils.df_info_to_string(df, with_sample=True))
    utils.log_memusage(logger)

    # logger.info(f"creating graph from dataframe ")
    # g = igraph.Graph.DataFrame(df, directed=True, use_vids=False)
    # logger.info(g.summary())
    gfile = f"{path_prefix}_ig.pkl"
    # logger.info(f"reading {gfile}")
    # with open(gfile, 'rb') as pickle_file:
    #   pickled_data = bytearray(pickle_file.read())
    logger.info(f"unpickling {gfile}")
    # g = pickle.loads(pickled_data)
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

    graphs[GraphType.engagement] = self.load_graph(settings.ENGAGEMENT_GRAPH_PATHPREFIX, GraphType.engagement)
    logger.info(f"loaded {graphs[GraphType.engagement]}")

    graphs[GraphType.ninetydays] = self.load_graph(settings.NINETYDAYS_GRAPH_PATHPREFIX, GraphType.ninetydays)
    logger.info(f"loaded {graphs[GraphType.ninetydays]}")

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
          # signal to the load balancer to stop sending new requests
          # TODO co-ordinate with other servers to avoid all
          # ... load-balanced servers going down at the same time
          main.get_pause()
          time.sleep(settings.PAUSE_BEFORE_RELOAD_SECS)
          logger.info("reload graphs")
          self.graphs = self.load_graphs()
          main.get_resume() # start accepting new requests
          break
    except Exception as e:
      logger.error(e)
    except:
      logger.error("something bad happened")
    return

import os
import math

from . import utils 
from .config import settings
from .models.graph_model import PlGraph

import polars as pl
from loguru import logger

class GraphLoader:

  def __init__(self) -> None:
    self.graph = self.load_graph(settings.PLGRAPH_PATHPREFIX)

  def get_graph(self):
    return self.graph

  def load_graph(self, path_prefix):
    sfile = f"{path_prefix}_SUCCESS"
    plfile = f"{path_prefix}.parquet"

    utils.log_memusage(logger)
    logger.info(f"loading graph from {plfile}")
    pl_df = pl.read_parquet(plfile)    
    utils.log_memusage(logger)

    logger.info(f"sorting graph: {pl_df.flags}")
    pl_df = pl_df.sort('fid')
    logger.info(f"graph: {pl_df}")
    pl_graph = PlGraph(
      success_file=sfile,
      df=pl_df,
      mtime=os.path.getmtime(sfile),
    )
    logger.info(f"loaded and sorted graph: {pl_graph}")
    utils.log_memusage(logger)
    return pl_graph

  def reload_if_required(self):
    logger.info("checking graphs mtime")
    try:
      model = self.graph
      is_graph_modified = not math.isclose(model.mtime, os.path.getmtime(model.success_file), rel_tol=1e-9)
      logger.debug(
                    f"In-memory mtime {model.mtime},"
                    f" OS mtime {os.path.getmtime(model.success_file)}"
                    f" {"are not close" if is_graph_modified else "are close"}"
                  )
      if is_graph_modified:
        logger.info("reload graph")
        self.graph = self.load_graph(settings.PLGRAPH_PATHPREFIX)
    except Exception as e:
      logger.error(e)
    except:
      logger.error("something bad happened")
    return

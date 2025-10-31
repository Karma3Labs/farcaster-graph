import gc
import math
import os
import time

import igraph
import pandas
from loguru import logger

from . import utils
from .config import settings
from .models.graph_model import Graph, GraphType
from .serverstatus import ServerStatus


class GraphLoader:

    def __init__(self, *poargs, server_status: ServerStatus, **kwargs) -> None:
        super().__init__(*poargs, **kwargs)
        self.graphs = self.load_graphs()
        self.server_status = server_status

    def get_graphs(self):
        return self.graphs

    @staticmethod
    def load_graph(path_prefix, graph_type: GraphType):
        s_file = f"{path_prefix}_SUCCESS"
        d_file = f"{path_prefix}_df.pkl"

        utils.log_memusage(logger)
        logger.info(f"unpickling {d_file}")
        df = pandas.read_pickle(d_file)
        logger.info(utils.df_info_to_string(df, with_sample=True))
        utils.log_memusage(logger)

        # logger.info(f"creating graph from dataframe ")
        # g = igraph.Graph.DataFrame(df, directed=True, use_vids=False)
        # logger.info(g.summary())
        g_file = f"{path_prefix}_ig.pkl"
        # logger.info(f"reading {g_file}")
        # with open(g_file, 'rb') as pickle_file:
        #   pickled_data = bytearray(pickle_file.read())
        logger.info(f"unpickling {g_file}")
        # g = pickle.loads(pickled_data)
        g = igraph.Graph.Read_Pickle(g_file)
        utils.log_memusage(logger)

        return Graph(
            success_file=s_file,
            df=df,
            graph=g,
            type=graph_type,
            mtime=os.path.getmtime(s_file),
        )

    def load_graphs(self) -> dict:
        # TODO use TypedDict or a pydantic model
        graphs = {
            GraphType.following: self.load_graph(
                settings.FOLLOW_GRAPH_PATH_PREFIX, GraphType.following
            )
        }

        # TODO fix hardcoding of name -> file, type of model
        logger.info(f"loaded {graphs[GraphType.following]}")

        # graphs[GraphType.engagement] = self.load_graph(settings.ENGAGEMENT_GRAPH_PATH_PREFIX, GraphType.engagement)
        # logger.info(f"loaded {graphs[GraphType.engagement]}")

        graphs[GraphType.ninety_days] = self.load_graph(
            settings.NINETY_DAYS_GRAPH_PATH_PREFIX, GraphType.ninety_days
        )
        logger.info(f"loaded {graphs[GraphType.ninety_days]}")

        return graphs

    def reload_if_required(self):
        logger.info("checking graphs mtime")
        try:
            for _, model in self.graphs.items():
                is_graph_modified = not math.isclose(
                    model.mtime, os.path.getmtime(model.success_file), rel_tol=1e-9
                )
                logger.debug(
                    f"In-memory mtime {model.mtime},"
                    f" OS mtime {os.path.getmtime(model.success_file)}"
                    f" {"are not close" if is_graph_modified else "are close"}"
                )
                if is_graph_modified:
                    # signal to the load balancer to stop sending new requests
                    # TODO co-ordinate with other servers to avoid all
                    # ... load-balanced servers going down at the same time
                    self.server_status.pause()
                    time.sleep(settings.PAUSE_BEFORE_RELOAD_SECS)
                    logger.info("reload graphs")
                    del self.graphs
                    gc.collect()
                    self.graphs = self.load_graphs()
                    self.server_status.resume()  # start accepting new requests
                    break
        except Exception as e:
            logger.error(e)
        return

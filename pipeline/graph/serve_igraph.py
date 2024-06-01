import sys
import time
import logging as log

from fastapi import FastAPI, Depends, Request, Response
from contextlib import asynccontextmanager
import uvicorn
import igraph

from config import settings

from loguru import logger

logger.remove()
level_per_module = {
    "": "INFO",
    "app": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout, 
           colorize=True, 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>",
           filter=level_per_module,
           level=0)


app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Execute when API is started"""
    logger.warning(f"{settings}")
    logger.warning(f"loading graph")
    g = igraph.Graph.Read_Pickle(settings.PERSONAL_IGRAPH_INPUT)
    app_state['graph'] = g
    logger.warning(f"graph loaded: {igraph.summary(g)}")
    yield
    """Execute when API is shutdown"""

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def session_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    logger.info(f"{request.method} {request.url}")
    response = Response("Internal server error", status_code=500)
    request.state.graph = app_state['graph']
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{request.url} took {elapsed_time} secs")
    return response


def inject_graph(request: Request) -> igraph.Graph:
  return request.state.graph

@app.get("/graph")
def get_graph(
  fid: int,
  k: int,
  limit: int,
  graph: igraph.Graph = Depends(inject_graph)
):
  try:
    vid = graph.vs.find(name=fid).index
  except:
    logger.error(f"{fid} NOT FOUND in graph.")
    return []
  neighbors = graph.neighborhood(vid, order=k, mode="out", mindist=k)
  if len(neighbors) == 0:
    logger.error(f"No {k}-degree neighbors for FID {fid}")
    return []
  k_neighbors_list = graph.vs[neighbors[:limit]]["name"]
  return k_neighbors_list



@app.get("/_health", status_code=200)
def get_health():
  logger.info("health check")
  return {'status': 'ok'}


if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)
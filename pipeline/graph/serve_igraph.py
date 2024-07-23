import sys
import time
from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.concurrency import run_in_threadpool
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
    logger.warning(f"loading graph {settings.PERSONAL_IGRAPH_INPUT}")
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
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{request.url} took {elapsed_time} secs")
    return response

def inject_graph(request: Request) -> igraph.Graph:
    return app_state['graph']

async def get_graph_neighbors(graph: igraph.Graph, fid: int, k: int, limit: int):
    try:
        vid = graph.vs.find(name=fid).index
        neighbors = await run_in_threadpool(graph.neighborhood, vid, order=k, mode="out", mindist=k)
        if len(neighbors) == 0:
            logger.error(f"No {k}-degree neighbors for FID {fid}")
            return []
        k_neighbors_list = graph.vs[neighbors[:limit]]["name"]
        return k_neighbors_list
    except Exception as e:
        logger.error(f"Error processing FID {fid}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing FID {fid}")

@app.get("/graph")
async def get_graph(
    fid: int,
    k: int,
    limit: int,
    graph: igraph.Graph = Depends(inject_graph)
):
    try:
        return await get_graph_neighbors(graph, fid, k, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/_reload", status_code=200)
async def reload_graph():
    try:
        logger.warning(f"reloading graph from {settings.PERSONAL_IGRAPH_INPUT}")
        g = await run_in_threadpool(igraph.Graph.Read_Pickle, settings.PERSONAL_IGRAPH_INPUT)
        app_state['graph'] = g
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Error reloading graph: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reloading graph")

@app.get("/_health", status_code=200)
def get_health():
    logger.info("health check")
    return {'status': 'ok'}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
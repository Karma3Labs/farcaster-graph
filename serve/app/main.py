import sys
import os
import time
import logging as log

from fastapi import FastAPI, Depends, Request, Response

from contextlib import asynccontextmanager
import uvicorn
import asyncio
import asyncpg
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id

from .dependencies import logging
from .config import settings
from .graph_loader import GraphLoader
from .routers.localtrust_router import router as lt_router
from .routers.globaltrust_router import router as gt_router
from .routers.channel_router import router as channel_router
from .routers.cast_router import router as cast_router

from loguru import logger

from .telemetry import PrometheusMiddleware, metrics


logger.remove()
level_per_module = {
   "": settings.LOG_LEVEL,
   "app.dependencies": settings.LOG_LEVEL_CORE,
   "uvicorn.access": False
}

def custom_log_filter(record):
    # Reference https://github.com/Delgan/loguru/blob/master/loguru/_filters.py
    # https://loguru.readthedocs.io/en/stable/api/logger.html#record
    record['correlation_id'] = correlation_id.get()
    name = record["name"]
    if not name:
        return False
    level = level_per_module.get(name, None)
    if level is not None:
        if record["level"].no >= level:
            return False
    return True

logger.add(sys.stdout, 
           colorize=True,
           format=settings.LOGURU_FORMAT,
           filter=custom_log_filter)

log.basicConfig(handlers=[logging.InterceptHandler()], level=0, force=True)
log.getLogger("uvicorn").handlers = [logging.InterceptHandler()]
log.getLogger("uvicorn.access").handlers = [logging.InterceptHandler()]

app_state = {}

async def check_and_reload_models(loader: GraphLoader):
    loop = asyncio.get_running_loop()
    logger.info("Starting graph loader loop")
    while True:
        await asyncio.sleep(settings.RELOAD_FREQ_SECS)
        await loop.run_in_executor(
            executor=None, func=loader.reload_if_required
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Execute when API is started"""
    logger.warning(f"{settings}")
    app_state['graph_loader'] = GraphLoader()
    app_state['graph_loader_task'] = asyncio.create_task(
        check_and_reload_models(app_state['graph_loader'])
    )
    app_state['db_pool'] = await asyncpg.create_pool(settings.POSTGRES_URI.get_secret_value(),
                                         min_size=1,
                                         max_size=settings.POSTGRES_POOL_SIZE)
    yield
    """Execute when API is shutdown"""
    await app_state['db_pool'].close()
    app_state['graph_loader_task'].cancel()

APP_NAME = "farcaster-openrank-neynar"

app = FastAPI(lifespan=lifespan, dependencies=[Depends(logging.get_logger)], title='Karma3Labs')

app.add_middleware(CorrelationIdMiddleware)

# Everything other than For You feed is out of scope
# app.include_router(lt_router, prefix='/scores/global')
# app.include_router(lt_router, prefix='/scores/personalized')
# app.include_router(channel_router, prefix='/channels')
app.include_router(cast_router, prefix='/casts')


# Setting metrics middleware
app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)
app.add_route("/metrics", metrics)

@app.middleware("http")
async def session_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    logger.info(f"{request.method} {request.url}")
    response = Response("Internal server error", status_code=500)
    request.state.graphs = app_state['graph_loader'].get_graphs()
    request.state.db_pool = app_state['db_pool']
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{request.url} took {elapsed_time} secs")
    return response

@app.get("/_health", status_code=200)
def get_health():
    logger.info("health check")
    return {'status': 'ok'}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
import sys
import time
import logging as log

from fastapi import FastAPI, Depends, Request, Response
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import asyncpg

from .dependencies import logging
from .config import settings
from .graph_loader import GraphLoader
from .graph_router import router as graph_router

from loguru import logger

logger.remove()
logger.add(sys.stdout, colorize=True, 
           format="<green>{time:HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>",
           level=settings.LOG_LEVEL)

log.basicConfig(handlers=[logging.InterceptHandler()], level=0, force=True)
log.getLogger("uvicorn").handlers = [logging.InterceptHandler()]
log.getLogger("uvicorn.access").handlers = [logging.InterceptHandler()]
# Since we launch uvicorn from command-line and not in code uvicorn.run,
# changing LOGGING_CONFIG has no effect.
# from uvicorn.config import LOGGING_CONFIG
# LOGGING_CONFIG["formatters"]["access"]["fmt"] = \
#     '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'

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
    app_state['graph_loader'] = GraphLoader()
    app_state['graph_loader_task'] = asyncio.create_task(
        check_and_reload_models(app_state['graph_loader'])
    )
    logger.info(f"****WARNING****: {settings.POSTGRES_URI}")
    app_state['db_pool'] = await asyncpg.create_pool(settings.POSTGRES_URI, 
                                         min_size=1, 
                                         max_size=settings.POSTGRES_POOL_SIZE)
    yield
    """Execute when API is shutdown"""
    await app_state['db_pool'].close()
    app_state['graph_loader_task'].cancel()

app = FastAPI(lifespan=lifespan, dependencies=[Depends(logging.get_logger)])
app.include_router(graph_router, prefix='/graph')

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
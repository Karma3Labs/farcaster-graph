import sys
import os
import time
import logging as log

from fastapi import FastAPI, Depends, Request, Response
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
import uvicorn
import asyncio
import asyncpg

from .dependencies import logging
from .config import settings
from .graph_loader import GraphLoader
from .routers.direct_router import router as direct_router
from .routers.graph_router import router as graph_router
from .routers.metadata_router import router as metadata_router
from .routers.localtrust_router import router as lt_router
from .routers.globaltrust_router import router as gt_router
from .routers.frame_router import router as frame_router

from loguru import logger

from opentelemetry.propagate import inject
from .telemetry import PrometheusMiddleware, metrics, setting_otlp


logger.remove()
logger.add(sys.stdout, colorize=True, 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>",
           level=settings.LOG_LEVEL)

log.basicConfig(handlers=[logging.InterceptHandler()], level=0, force=True)
log.getLogger("uvicorn").handlers = [logging.InterceptHandler()]
log.getLogger("uvicorn.access").handlers = [logging.InterceptHandler()]
# Since we launch uvicorn from command-line and not in code uvicorn.run,
# changing LOGGING_CONFIG has no effect.
# from uvicorn.config import LOGGING_CONFIG
# LOGGING_CONFIG["formatters"]["access"]["fmt"] = \
#     '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
class EndpointFilter(log.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: log.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1

# Filter out /metrics
log.getLogger("uvicorn.access").addFilter(EndpointFilter())

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Farcaster Graph by Karma3Labs",
        version="1.0.0",
        summary="OpenAPI schema",
        description="This API provides reputation graphs based on social interactions on the Farcaster Protocol",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "/static/favicon.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

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
    app_state['db_pool'] = await asyncpg.create_pool(settings.POSTGRES_URI.get_secret_value(), 
                                         min_size=1, 
                                         max_size=settings.POSTGRES_POOL_SIZE)
    app_state['graph_loader'] = GraphLoader()
    app_state['graph_loader_task'] = asyncio.create_task(
        check_and_reload_models(app_state['graph_loader'])
    )
    yield
    """Execute when API is shutdown"""
    await app_state['db_pool'].close()
    app_state['graph_loader_task'].cancel()

# TODO: change this to os env var once blue-green deployment is set up
APP_NAME = "farcaster-graph-a" #os.environ.get("APP_NAME", "farcaster-graph-a")

app = FastAPI(lifespan=lifespan, dependencies=[Depends(logging.get_logger)], title='Karma3Labs', docs_url=None)
app.include_router(direct_router, prefix='/links')
app.include_router(graph_router, prefix='/graph')
app.include_router(metadata_router, prefix='/metadata')
app.include_router(lt_router, prefix='/scores/personalized')
app.include_router(gt_router, prefix='/scores/global')
app.include_router(frame_router, prefix='/frames')

app.openapi = custom_openapi
app.mount("/static", StaticFiles(directory="static"), name="static")

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


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Farcaster Graph by Karma3Labs",
        swagger_favicon_url="/static/favicon.png"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
import asyncio
import logging as log
import sys
import time
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from cashews import cache
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config import settings
from .dependencies import logging
from .graph_loader import GraphLoader
from .routers.cast_router import router as cast_router
from .routers.channel_router import router as channel_router
from .routers.direct_router import router as direct_router
from .routers.globaltrust_router import router as gt_router
from .routers.graph_router import router as graph_router
from .routers.localtrust_router import router as lt_router
from .routers.metadata_router import router as metadata_router
from .routers.token_router import router as token_router
from .routers.user_router import router as user_router
from .serverstatus import ServerStatus
from .telemetry import PrometheusMiddleware, metrics

cache.setup("disk://", directory="/tmp/farcaster-serve-diskcache")


logger.remove()
level_per_module = {
    "": logger.level(settings.LOG_LEVEL),
    "app.dependencies.db_utils": logger.level(settings.LOG_LEVEL_CORE),
    "app.graph_loader": logger.level(settings.LOG_LEVEL_CORE),
    "uvicorn.access": None,
}


def custom_log_filter(record):
    # Reference https://github.com/Delgan/loguru/blob/master/loguru/_filters.py
    # https://loguru.readthedocs.io/en/stable/api/logger.html#record
    record["correlation_id"] = correlation_id.get()
    name = record["name"]
    if not name:
        return False
    level = level_per_module.get(name, level_per_module.get("", None))
    if level is not None:
        if record["level"].no < level.no:
            return False
    return True


logger.add(
    sys.stdout, colorize=True, format=settings.LOGURU_FORMAT, filter=custom_log_filter
)

# logger.add(sys.stdout,
#            colorize=True,
#            format=settings.LOGURU_FORMAT,
#            filter=level_per_module,
#            level=0)

log.basicConfig(handlers=[logging.InterceptHandler()], level=0, force=True)
log.getLogger("uvicorn").handlers = [logging.InterceptHandler()]
log.getLogger("uvicorn.access").handlers = [logging.InterceptHandler()]
# Since we launch uvicorn from the command-line and not in code uvicorn.run,
# changing LOGGING_CONFIG has no effect.
# from uvicorn.config import LOGGING_CONFIG
# LOGGING_CONFIG["formatters"]["access"]["fmt"] = \
#     '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'


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
    openapi_schema["info"]["x-logo"] = {"url": "/static/favicon.png"}
    openapi_schema["servers"] = [{"url": settings.SWAGGER_BASE_URL}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app_state = {}
server_status = ServerStatus()


async def _check_and_reload_models(loader: GraphLoader):
    loop = asyncio.get_running_loop()
    logger.info("Starting graph loader loop")
    while True:
        await asyncio.sleep(settings.RELOAD_FREQ_SECS)
        # noinspection PyTypeChecker
        # (erroneously calls out that arguments are missing - they're optional)
        await loop.run_in_executor(executor=None, func=loader.reload_if_required)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Automatically called by FastAPI when the server is started"""
    logger.warning(f"{settings}")

    # create a DB connection pool
    logger.info("Creating DB pool")
    pool = asyncpg.create_pool(
        settings.postgres_uri.get_secret_value(),
        min_size=1,
        max_size=settings.POSTGRES_POOL_SIZE,
    )
    app_state["db_pool"] = await pool
    logger.info("DB pool created")

    if settings.CACHE_DB_ENABLED:
        logger.info("Creating a Cache DB pool")
        pool = asyncpg.create_pool(
            settings.cache_postgres_uri.get_secret_value(),
            min_size=1,
            max_size=settings.CACHE_POSTGRES_POOL_SIZE,
        )
        app_state["cache_db_pool"] = await pool
        logger.info("Cache DB pool created")
    else:
        app_state["cache_db_pool"] = None

    logger.info("Loading graphs")
    # Create a singleton instance of GraphLoader
    # ... load graphs from the disk immediately
    # ... set the loader into the global state
    # ... that every API request has access to.
    app_state["graph_loader"] = GraphLoader(server_status=server_status)

    # start a background thread that can reload graphs if necessary
    app_state["graph_loader_task"] = asyncio.create_task(
        _check_and_reload_models(app_state["graph_loader"])
    )
    logger.info("Graphs loaded")

    yield
    """Execute when the server is shutdown"""
    logger.info("Closing DB pool")
    await app_state["db_pool"].close()

    if settings.CACHE_DB_ENABLED:
        logger.info("Closing the Cache DB pool")
        await app_state["cache_db_pool"].close()

    logger.info("Closing graph loader")
    app_state["graph_loader_task"].cancel()


# TODO: change this to os env var once blue-green deployment is set up
APP_NAME = "farcaster-graph-a"  # os.environ.get("APP_NAME", "farcaster-graph-a")

app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(logging.get_logger)],
    title="Karma3Labs",
    docs_url=None,
)

# noinspection PyTypeChecker
app.add_middleware(CorrelationIdMiddleware)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(direct_router, prefix="/links")
app.include_router(graph_router, prefix="/graph")
app.include_router(metadata_router, prefix="/metadata")
app.include_router(lt_router, prefix="/scores/personalized")
app.include_router(gt_router, prefix="/scores/global")
# Decommission Frames ranking due to lack of usage
# ... and relevance with the introduction of Frames V2 by Warpcast
# app.include_router(frame_router, prefix='/frames')
app.include_router(cast_router, prefix="/casts")
app.include_router(channel_router, prefix="/channels")
app.include_router(user_router, prefix="/users")
app.include_router(token_router, prefix="/tokens")

app.openapi = custom_openapi
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setting metrics middleware
# noinspection PyTypeChecker
app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)
app.add_route("/metrics", metrics)


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """FastAPI automatically invokes this function for every http call"""
    start_time = time.perf_counter()
    logger.info(f"{request.method} {request.url}")
    request.state.graphs = app_state["graph_loader"].get_graphs()
    request.state.db_pool = app_state["db_pool"]
    request.state.cache_db_pool = app_state["cache_db_pool"]
    # call_next is a built-in FastAPI function that calls the actual API
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{request.url} took {elapsed_time} secs")
    return response


@app.get("/_health", include_in_schema=False)
def get_health(response: Response):
    app_status = server_status.status
    logger.info(f"health: {app_status}")
    if app_status != "accept":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response.headers["Retry-After"] = "300"  # retry after 5 mins
        return {"detail": "Service Unavailable"}
    return {"status": "ok"}


@app.get("/_pause", status_code=200, include_in_schema=False)
def get_pause():
    logger.info("pausing app")
    server_status.pause()
    return {"status": "ok"}


@app.get("/_resume", status_code=200, include_in_schema=False)
def get_resume():
    logger.info("resuming app")
    server_status.resume()
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Farcaster Graph by Karma3Labs",
        swagger_favicon_url="/static/favicon.png",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

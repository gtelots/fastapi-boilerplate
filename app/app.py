"""FastAPI application setup."""

import contextlib
from collections.abc import AsyncIterator
from typing import TypedDict

import structlog
from fastapi import FastAPI
from fastapi.routing import APIRoute

from app import worker  # noqa
from app.api import router
from app.config import app_settings
from app.exception_handlers import add_exception_handlers
from app.health.endpoints import router as health_router
from app.kit.cors import CORSConfig, CORSMatcherMiddleware, Scope
from app.kit.db.postgres import (
    AsyncEngine,
    AsyncSessionMaker,
    Engine,
    SyncSessionMaker,
    create_async_sessionmaker,
    create_sync_sessionmaker,
)
from app.logfire import (
    configure_logfire,
    instrument_fastapi,
    instrument_httpx,
    instrument_sqlalchemy,
)
from app.logging import Logger
from app.logging import configure as configure_logging
from app.middlewares import (
    FlushEnqueuedWorkerJobsMiddleware,
    LogCorrelationIdMiddleware,
    PathRewriteMiddleware,
    SandboxResponseHeaderMiddleware,
)
from app.openapi import OPENAPI_PARAMETERS, APITag, set_openapi_generator
from app.postgres import (
    AsyncSessionMiddleware,
    create_async_engine,
    create_sync_engine,
)
from app.redis import Redis, create_redis
# from app.sentry import configure_sentry

log: Logger = structlog.get_logger()


def configure_cors(app: FastAPI) -> None:
    configs: list[CORSConfig] = []

    # Frontend CORS configuration
    if app_settings.CORS_ORIGINS:

        def frontend_matcher(origin: str, scope: Scope) -> bool:
            return origin in app_settings.CORS_ORIGINS

        frontend_config = CORSConfig(
            frontend_matcher,
            allow_origins=[str(origin) for origin in app_settings.CORS_ORIGINS],
            allow_credentials=True,  # Cookies are allowed, but only there!
            allow_methods=["*"],
            allow_headers=["*"],
        )
        configs.append(frontend_config)

    # External API calls CORS configuration
    api_config = CORSConfig(
        lambda origin, scope: True,
        allow_origins=["*"],
        allow_credentials=False,  # No cookies allowed
        allow_methods=["*"],
        allow_headers=["Authorization"],  # Allow Authorization header to pass tokens
    )
    configs.append(api_config)

    app.add_middleware(CORSMatcherMiddleware, configs=configs)


def generate_unique_openapi_id(route: APIRoute) -> str:
    parts = [str(tag) for tag in route.tags if tag not in APITag] + [route.name]
    return ":".join(parts)


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker
    async_read_engine: AsyncEngine
    async_read_sessionmaker: AsyncSessionMaker
    sync_engine: Engine
    sync_sessionmaker: SyncSessionMaker

    redis: Redis


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    log.info("Starting API")

    async_engine = create_async_engine("app")
    async_sessionmaker = create_async_sessionmaker(
        async_engine
    )
    instrument_sqlalchemy(async_engine.sync_engine)

    sync_engine = create_sync_engine("app")
    sync_sessionmaker = create_sync_sessionmaker(sync_engine)
    instrument_sqlalchemy(sync_engine)

    redis = create_redis("app")

    log.info("API started")

    yield {
        "async_engine": async_engine,
        "async_sessionmaker": async_sessionmaker,
        "sync_engine": sync_engine,
        "sync_sessionmaker": sync_sessionmaker,
        "redis": redis,
    }

    await redis.close(True)
    await async_engine.dispose()
    sync_engine.dispose()

    log.info("API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        generate_unique_id_function=generate_unique_openapi_id,
        lifespan=lifespan,
        **OPENAPI_PARAMETERS,
    )

    # Middlewares
    if app_settings.is_sandbox():
        app.add_middleware(SandboxResponseHeaderMiddleware)
    if not app_settings.is_testing():
        app.add_middleware(FlushEnqueuedWorkerJobsMiddleware)
        app.add_middleware(AsyncSessionMiddleware)
    app.add_middleware(PathRewriteMiddleware, pattern=r"^/api/v1", replacement="/v1")
    app.add_middleware(LogCorrelationIdMiddleware)

    # CORS
    configure_cors(app)

    # Exception handlers
    add_exception_handlers(app)

    # /healthz
    app.include_router(health_router)

    # /v1
    app.include_router(router)

    return app


# configure_sentry()
configure_logfire("server")
configure_logging(logfire=True)

app = create_app()
set_openapi_generator(app)
instrument_fastapi(app)
instrument_httpx()

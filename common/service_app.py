"""Factory helpers for building FastAPI microservices with shared behaviour."""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .config import Settings, get_settings
from .rabbitmq import RabbitMQManager


RouteConfigurator = Callable[[FastAPI, RabbitMQManager, Settings], None]


def create_service_app(configure: RouteConfigurator | None = None) -> FastAPI:
    """Create a configured FastAPI application with shared middleware and lifecycle."""

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger = logging.getLogger(settings.service_name)

    app = FastAPI(
        title=f"MIAR {settings.service_name}",
        default_response_class=ORJSONResponse,
    )

    rabbitmq_manager = RabbitMQManager(str(settings.rabbitmq_url), service_role=settings.service_role)

    # attach to app state for reuse in routers/tests
    app.state.settings = settings
    app.state.rabbitmq = rabbitmq_manager

    @app.on_event("startup")
    async def on_startup() -> None:  # noqa: D401 - documented by function name
        await rabbitmq_manager.connect()
        logger.info("Service %s started", settings.service_name)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await rabbitmq_manager.close()
        logger.info("Service %s stopped", settings.service_name)

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:  # noqa: D401 - simple response
        return {"service": settings.service_name, "status": "ok"}

    if configure:
        configure(app, rabbitmq_manager, settings)

    return app


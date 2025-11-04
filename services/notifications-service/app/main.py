from __future__ import annotations

import asyncio
import logging
from collections import deque

import orjson
from aio_pika.abc import AbstractIncomingMessage
from fastapi import APIRouter

from common.service_app import create_service_app


events = deque(maxlen=100)


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/events")
async def get_events() -> dict[str, int]:
    return {"total": len(events)}


def configure_app(app, rabbitmq_manager, settings) -> None:
    logger = logging.getLogger(settings.service_name)

    async def on_service_event(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            events.append(payload)
            logger.info("Notification received: %s", payload.get("event_type"))

    async def on_workload(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            sleep_seconds = int(payload.get("sleep_seconds", 0))
            if sleep_seconds:
                logger.info("Notifications workload sleeping for %s seconds", sleep_seconds)
                await asyncio.sleep(sleep_seconds)
            events.append(payload)
            logger.info("Workload handled from %s", payload.get("source"))

    async def start_consumers() -> None:
        await rabbitmq_manager.consume_service_queue(settings.service_role, on_service_event)
        route = settings.symbol_route
        if route:
            await rabbitmq_manager.consume_workload(route.symbol, on_workload)

    app.include_router(router)
    app.add_event_handler("startup", start_consumers)


app = create_service_app(configure_app)

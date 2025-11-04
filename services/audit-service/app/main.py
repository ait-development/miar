from __future__ import annotations

import asyncio
import logging
from collections import deque

import orjson
from aio_pika.abc import AbstractIncomingMessage
from fastapi import APIRouter

from common.service_app import create_service_app


audit_log = deque(maxlen=200)


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
async def list_events() -> dict[str, int]:
    return {"events": len(audit_log)}


def configure_app(app, rabbitmq_manager, settings) -> None:
    logger = logging.getLogger(settings.service_name)

    async def on_service_event(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            audit_log.append(payload)
            logger.info("Audit event stored: %s", payload.get("event_type"))

    async def on_topic_workload(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            sleep_seconds = int(payload.get("sleep_seconds", 0))
            if sleep_seconds:
                logger.debug("Audit workload sleeping for %s seconds", sleep_seconds)
                await asyncio.sleep(sleep_seconds)
            audit_log.append(payload)
            logger.info("Topic workload logged from %s", payload.get("source"))

    async def start_consumers() -> None:
        await rabbitmq_manager.consume_service_queue(settings.service_role, on_service_event)
        route = settings.symbol_route
        if route:
            await rabbitmq_manager.consume_workload(route.symbol, on_topic_workload)

    app.include_router(router)
    app.add_event_handler("startup", start_consumers)


app = create_service_app(configure_app)

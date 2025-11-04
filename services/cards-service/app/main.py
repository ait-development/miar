from __future__ import annotations

import asyncio
import logging
from collections import deque

import orjson
from aio_pika.abc import AbstractIncomingMessage
from fastapi import APIRouter

from common.service_app import create_service_app


processed_events = deque(maxlen=50)


router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/events")
async def list_events() -> dict[str, int]:
    return {"processed": len(processed_events)}


def configure_app(app, rabbitmq_manager, settings) -> None:
    logger = logging.getLogger(settings.service_name)

    async def handle_card_requests(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            processed_events.append(payload)
            logger.info("Card request processed for customer %s", payload.get("customer_id"))

    async def handle_workload(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            sleep_seconds = int(payload.get("sleep_seconds", 0))
            if sleep_seconds:
                logger.info("Card workload sleeping for %s seconds", sleep_seconds)
                await asyncio.sleep(sleep_seconds)
            processed_events.append(payload)
            logger.info("Card workload from %s completed", payload.get("source"))

    async def start_consumers() -> None:
        await rabbitmq_manager.consume_service_queue(settings.service_role, handle_card_requests)
        route = settings.symbol_route
        if route:
            await rabbitmq_manager.consume_workload(route.symbol, handle_workload)

    app.include_router(router)
    app.add_event_handler("startup", start_consumers)


app = create_service_app(configure_app)

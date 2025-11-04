from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

import orjson
from aio_pika.abc import AbstractIncomingMessage
from fastapi import APIRouter, Request

from common.models import WorkloadRequest
from common.service_app import create_service_app


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/workload", status_code=202)
async def publish_workload(request_model: WorkloadRequest, request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    rabbitmq_manager = request.app.state.rabbitmq

    message = request_model.to_message(source=settings.service_name)
    await rabbitmq_manager.publish_workload(request_model.symbol, message)
    return {"status": "queued", "workload_id": message["workload_id"]}


def make_payment_consumer(logger, settings, rabbitmq_manager):
    async def _handler(message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = orjson.loads(message.body)
            logger.info(
                "Processed payment instruction %s", payload.get("instruction_id")
            )

            event = {
                "event_id": str(uuid4()),
                "event_type": "payment.processed",
                "source": settings.service_name,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload,
            }
            await rabbitmq_manager.publish_service_event(["notifications", "audit"], event)

            workload = {
                "workload_id": str(uuid4()),
                "symbol": "#",
                "sleep_seconds": min(int(payload.get("payload", {}).get("amount", 1)), 5),
                "source": settings.service_name,
                "payload": payload,
                "created_at": datetime.utcnow().isoformat(),
            }
            await rabbitmq_manager.publish_workload("#", workload)

    return _handler


def configure_app(app, rabbitmq_manager, settings) -> None:
    logger = logging.getLogger(settings.service_name)
    app.include_router(router)

    async def start_consumers() -> None:
        await rabbitmq_manager.consume_service_queue(
            settings.service_role,
            make_payment_consumer(logger, settings, rabbitmq_manager),
        )

    app.add_event_handler("startup", start_consumers)


app = create_service_app(configure_app)

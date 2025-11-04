from __future__ import annotations

from fastapi import APIRouter, Request

from common import constants
from common.models import CardRequest
from common.service_app import create_service_app


router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/cards", status_code=202)
async def request_card(card_request: CardRequest, request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    rabbitmq_manager = request.app.state.rabbitmq

    message = card_request.model_dump()
    await rabbitmq_manager.send_to_queue(constants.AUTO_DELETE_QUEUE, message, persistent=False)
    return {"status": "queued", "customer_id": card_request.customer_id}


def configure_app(app, rabbitmq_manager, settings) -> None:
    app.include_router(router)


app = create_service_app(configure_app)

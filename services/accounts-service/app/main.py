from __future__ import annotations

from fastapi import APIRouter, Request

from common import constants
from common.models import PaymentInstruction
from common.service_app import create_service_app


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/{account_id}/payments", status_code=202)
async def enqueue_payment(
    account_id: str,
    instruction: PaymentInstruction,
    request: Request,
) -> dict[str, str]:
    settings = request.app.state.settings
    rabbitmq_manager = request.app.state.rabbitmq

    payload = instruction.model_copy(update={"from_account": account_id})
    message = payload.to_queue_message(source=settings.service_name)
    await rabbitmq_manager.send_to_queue(constants.DURABLE_QUEUE, message, persistent=True)
    return {"status": "queued", "instruction_id": message["instruction_id"]}


def configure_app(app, rabbitmq_manager, settings) -> None:
    app.include_router(router)


app = create_service_app(configure_app)

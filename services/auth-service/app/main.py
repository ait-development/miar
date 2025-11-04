from __future__ import annotations

from fastapi import APIRouter, Request

from common.models import AuthEvent
from common.service_app import create_service_app


auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/events", status_code=202)
async def publish_auth_event(event: AuthEvent, request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    rabbitmq_manager = request.app.state.rabbitmq

    payload = event.to_service_event(source=settings.service_name)
    await rabbitmq_manager.publish_service_event(["notifications", "audit"], payload)
    return {"status": "queued", "event_id": payload["event_id"]}


def configure_app(app, rabbitmq_manager, settings) -> None:
    app.include_router(auth_router)


app = create_service_app(configure_app)

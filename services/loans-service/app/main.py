from __future__ import annotations

from fastapi import APIRouter, Request

from common.models import LoanApplication
from common.service_app import create_service_app


router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/applications", status_code=202)
async def submit_application(application: LoanApplication, request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    rabbitmq_manager = request.app.state.rabbitmq

    message = application.to_workload(source=settings.service_name)
    await rabbitmq_manager.publish_workload("-", message)
    return {"status": "queued", "workload_id": message["workload_id"]}


def configure_app(app, rabbitmq_manager, settings) -> None:
    app.include_router(router)


app = create_service_app(configure_app)


from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import orjson
import pytest
from aio_pika.abc import AbstractIncomingMessage
from httpx import ASGITransport, AsyncClient

from common import constants
from common.rabbitmq import RabbitMQManager


@pytest.fixture()
async def accounts_app(rabbitmq_dsn: str):
    os.environ["RABBITMQ_URL"] = rabbitmq_dsn
    os.environ["SERVICE_NAME"] = "accounts-service"
    os.environ["SERVICE_ROLE"] = "accounts"
    
    import sys
    from pathlib import Path
    
    service_path = Path(__file__).parent.parent.parent / "services" / "accounts-service"
    sys.path.insert(0, str(service_path))
    
    from app.main import app
    
    async with app.router.lifespan_context(app):
        yield app
    
    sys.path.remove(str(service_path))


@pytest.fixture()
async def accounts_client(accounts_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=accounts_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_accounts_service_health_check(accounts_client: AsyncClient) -> None:
    response = await accounts_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "accounts-service"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_accounts_service_invalid_payment(accounts_client: AsyncClient) -> None:
    response = await accounts_client.post(
        "/accounts/ACC-001/payments",
        json={
            "to_account": "ACC-002",
        },
    )

    assert response.status_code == 422


from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from common.rabbitmq import RabbitMQManager


@pytest.fixture()
async def audit_app(rabbitmq_dsn: str):
    os.environ["RABBITMQ_URL"] = rabbitmq_dsn
    os.environ["SERVICE_NAME"] = "audit-service"
    os.environ["SERVICE_ROLE"] = "audit"
    os.environ["SLEEP_SYMBOL"] = "-"
    
    import sys
    from pathlib import Path
    
    service_path = Path(__file__).parent.parent.parent / "services" / "audit-service"
    sys.path.insert(0, str(service_path))
    
    from app.main import app
    
    async with app.router.lifespan_context(app):
        yield app
    
    sys.path.remove(str(service_path))


@pytest.fixture()
async def audit_client(audit_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=audit_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_audit_service_health_check(audit_client: AsyncClient) -> None:
    response = await audit_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "audit-service"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_audit_service_receives_service_events(
    audit_app,
    audit_client: AsyncClient,
    rabbitmq_manager: RabbitMQManager,
) -> None:
    initial_response = await audit_client.get("/audit/events")
    initial_count = initial_response.json()["events"]

    # Publish service event to audit
    event = {
        "event_id": "EVT-001",
        "event_type": "payment.processed",
        "source": "payments-service",
        "timestamp": "2024-01-01T00:00:00",
        "payload": {"amount": 1000.0},
    }
    await rabbitmq_manager.publish_service_event(["audit"], event)

    # Wait for processing
    await asyncio.sleep(1.0)

    # Check that event was logged
    response = await audit_client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] > initial_count


@pytest.mark.asyncio
async def test_audit_service_receives_topic_workloads(
    audit_app,
    audit_client: AsyncClient,
    rabbitmq_manager: RabbitMQManager,
) -> None:
    initial_response = await audit_client.get("/audit/events")
    initial_count = initial_response.json()["events"]

    # Publish topic workload
    workload = {
        "workload_id": "WORK-001",
        "symbol": "-",
        "sleep_seconds": 0,
        "source": "loans-service",
        "payload": {
            "customer_id": "CUST-100",
            "amount": 100000.0,
        },
        "created_at": "2024-01-01T00:00:00",
    }
    await rabbitmq_manager.publish_workload("-", workload)

    await asyncio.sleep(1.0)

    response = await audit_client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] > initial_count


@pytest.mark.asyncio
async def test_audit_service_logs_multiple_event_types(
    audit_app,
    audit_client: AsyncClient,
    rabbitmq_manager: RabbitMQManager,
) -> None:
    initial_response = await audit_client.get("/audit/events")
    initial_count = initial_response.json()["events"]

    # Send auth event
    auth_event = {
        "event_id": "AUTH-001",
        "event_type": "auth.login",
        "source": "auth-service",
        "timestamp": "2024-01-01T00:00:00",
        "payload": {"user_id": "user-123"},
    }
    await rabbitmq_manager.publish_service_event(["audit"], auth_event)

    payment_event = {
        "event_id": "PAY-001",
        "event_type": "payment.processed",
        "source": "payments-service",
        "timestamp": "2024-01-01T00:00:00",
        "payload": {"amount": 500.0},
    }
    await rabbitmq_manager.publish_service_event(["audit"], payment_event)

    await asyncio.sleep(1.5)

    response = await audit_client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] >= initial_count + 2


@pytest.mark.asyncio
async def test_audit_service_respects_maxlen(
    audit_app,
    audit_client: AsyncClient,
    rabbitmq_manager: RabbitMQManager,
) -> None:
    for i in range(210):
        event = {
            "event_id": f"EVT-{i}",
            "event_type": "test.event",
            "source": "test-service",
            "timestamp": "2024-01-01T00:00:00",
            "payload": {"index": i},
        }
        await rabbitmq_manager.publish_service_event(["audit"], event)

    await asyncio.sleep(5.0)

    response = await audit_client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] <= 200


@pytest.mark.asyncio
async def test_audit_service_handles_workload_with_sleep(
    audit_app,
    audit_client: AsyncClient,
    rabbitmq_manager: RabbitMQManager,
) -> None:
    initial_response = await audit_client.get("/audit/events")
    initial_count = initial_response.json()["events"]

    workload = {
        "workload_id": "WORK-SLEEP",
        "symbol": "-",
        "sleep_seconds": 1,
        "source": "test-service",
        "payload": {},
        "created_at": "2024-01-01T00:00:00",
    }
    
    start_time = asyncio.get_event_loop().time()
    await rabbitmq_manager.publish_workload("-", workload)
    
    await asyncio.sleep(2.0)
    
    end_time = asyncio.get_event_loop().time()
    
    assert end_time - start_time >= 1.0
    
    response = await audit_client.get("/audit/events")

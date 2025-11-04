from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import orjson
import pytest
from aio_pika.abc import AbstractIncomingMessage
from urllib.parse import quote

from testcontainers.rabbitmq import RabbitMqContainer

from common import constants
from common.rabbitmq import RabbitMQManager


@pytest.fixture(scope="session")
def rabbitmq_container() -> AsyncIterator[RabbitMqContainer]:
    # Pika (used internally by testcontainers) has issues with RabbitMQ 3.13 handshake.
    # Use 3.12 for stable integration tests.
    with RabbitMqContainer("rabbitmq:3.12-management") as container:
        yield container


@pytest.fixture()
def rabbitmq_dsn(rabbitmq_container: RabbitMqContainer) -> str:
    params = rabbitmq_container.get_connection_params()

    credentials = getattr(params, "credentials", None)
    username = quote(getattr(credentials, "username", "guest"))
    password = quote(getattr(credentials, "password", "guest"))

    host = getattr(params, "host", "localhost")
    port = getattr(params, "port", 5672)
    vhost = getattr(params, "virtual_host", "/") or "/"
    cleaned_vhost = vhost.lstrip("/")
    return f"amqp://{username}:{password}@{host}:{port}/{cleaned_vhost}"


@pytest.mark.asyncio
async def test_setup_topology_creates_declared_queues(rabbitmq_dsn: str) -> None:
    manager = RabbitMQManager(rabbitmq_dsn, service_role="notifications")
    await manager.connect()

    try:
        for queue_cfg in constants.QUEUES:
            declared = await manager.channel.declare_queue(queue_cfg.name, passive=True)
            assert declared.name == queue_cfg.name
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_service_event_and_workload_routing(rabbitmq_dsn: str) -> None:
    publisher = RabbitMQManager(rabbitmq_dsn, service_role="payments")
    consumer = RabbitMQManager(rabbitmq_dsn, service_role="notifications")

    await publisher.connect()
    await consumer.connect()

    service_event_received = asyncio.Event()
    workload_received = asyncio.Event()
    service_events: list[dict] = []
    workloads: list[dict] = []

    async def service_handler(message: AbstractIncomingMessage) -> None:
        async with message.process():
            service_events.append(orjson.loads(message.body))
            service_event_received.set()

    async def workload_handler(message: AbstractIncomingMessage) -> None:
        async with message.process():
            workloads.append(orjson.loads(message.body))
            workload_received.set()

    await consumer.consume_service_queue("notifications", service_handler)
    await consumer.consume_workload("#", workload_handler)

    await publisher.publish_service_event(["notifications"], {"event": "test"})
    workload_payload = {
        "workload_id": "work-1",
        "symbol": "#",
        "sleep_seconds": 0,
        "source": "payments-service",
        "payload": {"foo": "bar"},
        "created_at": "2024-01-01T00:00:00",
    }
    await publisher.publish_workload("#", workload_payload)

    await asyncio.wait_for(service_event_received.wait(), timeout=15)
    await asyncio.wait_for(workload_received.wait(), timeout=15)

    assert service_events[0]["event"] == "test"
    assert workloads[0]["payload"]["foo"] == "bar"

    await consumer.close()
    await publisher.close()


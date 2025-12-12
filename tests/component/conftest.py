from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.rabbitmq import RabbitMqContainer

# Add project root to sys.path to import common module
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.rabbitmq import RabbitMQManager


@pytest.fixture(scope="session")
def rabbitmq_container() -> AsyncIterator[RabbitMqContainer]:
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


@pytest.fixture()
async def rabbitmq_manager(rabbitmq_dsn: str) -> AsyncIterator[RabbitMQManager]:
    manager = RabbitMQManager(rabbitmq_dsn, service_role="test")
    await manager.connect()
    yield manager
    await manager.close()


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def wait_for_message():
    async def _wait(event: asyncio.Event, timeout: float = 5.0):
        await asyncio.wait_for(event.wait(), timeout=timeout)
    return _wait


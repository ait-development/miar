"""RabbitMQ utilities shared across microservices."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Iterable

import orjson
from aio_pika import Connection, DeliveryMode, ExchangeType, Message, connect_robust
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustConnection,
)

from . import constants
from .constants import WorkloadRoute

LOGGER = logging.getLogger(__name__)


class RabbitMQManager:
    """Convenience wrapper that keeps a single connection/channel per service."""

    def __init__(self, dsn: str, service_role: str, prefetch_count: int = 10) -> None:
        self._dsn = dsn
        self._service_role = service_role
        self._prefetch_count = prefetch_count
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None
        self._consumer_tags: list[tuple[AbstractQueue, str]] = []

    @property
    def channel(self) -> AbstractRobustChannel:
        if self._channel is None:
            msg = "RabbitMQ channel is not initialised. Call connect() first."
            raise RuntimeError(msg)
        return self._channel

    async def connect(self) -> None:
        if self._connection:
            return
        LOGGER.info("Connecting to RabbitMQ: %s", self._dsn)
        self._connection = await connect_robust(self._dsn)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._prefetch_count)
        await setup_topology(self._channel, service_role=self._service_role)

    async def close(self) -> None:
        while self._consumer_tags:
            queue, tag = self._consumer_tags.pop()
            try:
                await queue.cancel(tag)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to cancel consumer %s on queue %s: %s", tag, queue.name, exc)

        if self._connection:
            LOGGER.info("Closing RabbitMQ connection")
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def publish_service_event(
        self,
        target_roles: Iterable[str],
        payload: dict[str, Any],
        persistent: bool = True,
    ) -> None:
        exchange = await self.channel.declare_exchange(
            constants.SERVICE_EVENT_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )

        delivery_mode = DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT
        message = Message(
            body=orjson.dumps(payload),
            delivery_mode=delivery_mode,
            content_type="application/json",
        )

        for role in target_roles:
            routing_key = constants.SERVICE_ROUTING_KEYS.get(role)
            if not routing_key:
                LOGGER.warning("Skipping publish to unknown service role '%s'", role)
                continue
            LOGGER.debug("Publishing service event to %s via routing key %s", role, routing_key)
            await exchange.publish(message, routing_key=routing_key)

    async def publish_workload(self, symbol: str, payload: dict[str, Any]) -> None:
        route = constants.SYMBOL_ROUTES.get(symbol)
        if route is None:
            msg = f"Unknown workload symbol '{symbol}'"
            raise ValueError(msg)

        exchange = await self.channel.declare_exchange(
            route.exchange,
            ExchangeType(route.exchange_type),
            durable=route.durable,
        )

        message = Message(
            body=orjson.dumps(payload),
            delivery_mode=(
                DeliveryMode.PERSISTENT if route.persistent_messages else DeliveryMode.NOT_PERSISTENT
            ),
            content_type="application/json",
            headers={"symbol": symbol},
        )

        routing_key = route.routing_key or ""
        LOGGER.debug(
            "Publishing workload message: exchange=%s routing_key=%s persistent=%s",
            route.exchange,
            routing_key,
            route.persistent_messages,
        )
        await exchange.publish(message, routing_key=routing_key)

    async def send_to_queue(
        self,
        queue_name: str,
        payload: dict[str, Any],
        persistent: bool = True,
    ) -> None:
        config_map = {cfg.name: cfg for cfg in constants.QUEUES}
        queue_cfg = config_map.get(queue_name)
        durable = queue_cfg.durable if queue_cfg else persistent
        queue = await self.channel.declare_queue(
            queue_name,
            durable=durable,
            exclusive=queue_cfg.exclusive if queue_cfg else False,
            auto_delete=queue_cfg.auto_delete if queue_cfg else False,
        )
        message = Message(
            body=orjson.dumps(payload),
            delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT,
            content_type="application/json",
        )
        default_exchange = self.channel.default_exchange
        await default_exchange.publish(message, routing_key=queue.name)

    async def consume_queue(
        self,
        queue_name: str,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        config_map = {cfg.name: cfg for cfg in constants.QUEUES}
        queue_cfg = config_map.get(queue_name)
        durable = queue_cfg.durable if queue_cfg else True
        exclusive = queue_cfg.exclusive if queue_cfg else False
        auto_delete = queue_cfg.auto_delete if queue_cfg else False

        queue = await self.channel.declare_queue(
            queue_name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
        )
        consumer_tag = await queue.consume(handler)
        self._consumer_tags.append((queue, consumer_tag))

    async def consume_service_queue(
        self,
        service_role: str,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        queue_name = constants.SERVICE_QUEUES_BY_ROLE.get(service_role)
        if not queue_name:
            msg = f"Unknown service role '{service_role}'"
            raise ValueError(msg)
        await self.consume_queue(queue_name, handler)

    async def consume_workload(
        self,
        symbol: str,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        route = constants.SYMBOL_ROUTES.get(symbol)
        if not route:
            msg = f"Unknown workload symbol '{symbol}'"
            raise ValueError(msg)

        await self.consume_queue_for_route(route, handler)

    async def consume_queue_for_route(
        self,
        route: WorkloadRoute,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        queues = [
            q
            for role, q in constants.SERVICE_QUEUES_BY_ROLE.items()
            if constants.SERVICE_SYMBOL_BY_ROLE.get(role) == route.symbol
        ]
        if not queues:
            LOGGER.warning("No queues configured for route symbol %s", route.symbol)
            return

        for queue_name in queues:
            await self.consume_queue(queue_name, handler)


async def setup_topology(channel: AbstractChannel, service_role: str | None = None) -> None:
    """Declare queues and exchanges required by the project."""

    LOGGER.debug("Declaring base queues")
    declared_queues: dict[str, AbstractQueue] = {}
    for queue_cfg in constants.QUEUES:
        if queue_cfg.exclusive and queue_cfg.owner_roles:
            if service_role not in queue_cfg.owner_roles:
                continue
        queue = await channel.declare_queue(
            queue_cfg.name,
            durable=queue_cfg.durable,
            exclusive=queue_cfg.exclusive,
            auto_delete=queue_cfg.auto_delete,
        )
        declared_queues[queue_cfg.name] = queue

    LOGGER.debug("Declaring service exchange and bindings")
    service_exchange = await channel.declare_exchange(
        constants.SERVICE_EVENT_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    for role, queue_name in constants.SERVICE_QUEUES_BY_ROLE.items():
        routing_key = constants.SERVICE_ROUTING_KEYS.get(role)
        if not routing_key:
            continue
        queue = declared_queues.get(queue_name)
        if queue is None:
            continue
        await queue.bind(service_exchange, routing_key=routing_key)

    LOGGER.debug("Declaring workload exchanges and bindings")
    for route in constants.SYMBOL_ROUTES.values():
        exchange = await channel.declare_exchange(
            route.exchange,
            ExchangeType(route.exchange_type),
            durable=route.durable,
        )

        for role, symbol in constants.SERVICE_SYMBOL_BY_ROLE.items():
            if symbol != route.symbol:
                continue
            queue_name = constants.SERVICE_QUEUES_BY_ROLE.get(role)
            if not queue_name:
                continue
            queue = declared_queues.get(queue_name)
            if queue is None:
                continue
            routing_key = route.routing_key or ""
            await queue.bind(exchange, routing_key=routing_key)


@asynccontextmanager
async def rabbitmq_channel(dsn: str, prefetch_count: int = 10, service_role: str | None = None):
    connection: Connection | None = None
    channel: AbstractChannel | None = None
    try:
        connection = await connect_robust(dsn)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=prefetch_count)
        await setup_topology(channel, service_role=service_role)
        yield channel
    finally:
        if channel:
            await channel.close()
        if connection:
            await connection.close()


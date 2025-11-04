"""Constants describing RabbitMQ topology for the project."""

from __future__ import annotations

from dataclasses import dataclass


GROUP_PREFIX = "ikbo-27-22"


EXCLUSIVE_QUEUE = f"{GROUP_PREFIX}_lokkhovGA"
DURABLE_QUEUE = f"{GROUP_PREFIX}_Sykchina"
AUTO_DELETE_QUEUE = f"{GROUP_PREFIX}_Tropetz"
AUDIT_QUEUE = f"{GROUP_PREFIX}_ryadnov"


FANOUT_EXCHANGE = f"{GROUP_PREFIX}.exchange.broadcast"
DIRECT_EXCHANGE = f"{GROUP_PREFIX}.exchange.direct"
TOPIC_EXCHANGE = f"{GROUP_PREFIX}.exchange.topic"
SERVICE_EVENT_EXCHANGE = f"{GROUP_PREFIX}.exchange.services"


@dataclass(frozen=True)
class QueueConfig:
    """Declarative description of a queue to be created."""

    name: str
    durable: bool = False
    exclusive: bool = False
    auto_delete: bool = False
    owner_roles: tuple[str, ...] | None = None


@dataclass(frozen=True)
class WorkloadRoute:
    """Routing metadata for task 5 workload processing."""

    symbol: str
    exchange: str
    exchange_type: str
    routing_key: str | None
    durable: bool
    persistent_messages: bool


QUEUES: tuple[QueueConfig, ...] = (
    QueueConfig(name=EXCLUSIVE_QUEUE, exclusive=True, owner_roles=("notifications",)),
    QueueConfig(name=DURABLE_QUEUE, durable=True),
    QueueConfig(name=AUTO_DELETE_QUEUE, auto_delete=True),
    QueueConfig(name=AUDIT_QUEUE, durable=True),
)


SYMBOL_ROUTES: dict[str, WorkloadRoute] = {
    "#": WorkloadRoute(
        symbol="#",
        exchange=FANOUT_EXCHANGE,
        exchange_type="fanout",
        routing_key=None,
        durable=True,
        persistent_messages=True,
    ),
    "*": WorkloadRoute(
        symbol="*",
        exchange=DIRECT_EXCHANGE,
        exchange_type="direct",
        routing_key=f"{GROUP_PREFIX}.workload.star",
        durable=False,
        persistent_messages=False,
    ),
    "-": WorkloadRoute(
        symbol="-",
        exchange=TOPIC_EXCHANGE,
        exchange_type="topic",
        routing_key=f"{GROUP_PREFIX}.workload.minus",
        durable=True,
        persistent_messages=True,
    ),
}


SERVICE_QUEUES_BY_ROLE: dict[str, str] = {
    "notifications": EXCLUSIVE_QUEUE,
    "payments": DURABLE_QUEUE,
    "cards": AUTO_DELETE_QUEUE,
    "audit": AUDIT_QUEUE,
}


SERVICE_ROUTING_KEYS: dict[str, str] = {
    "notifications": f"{GROUP_PREFIX}.services.notifications",
    "payments": f"{GROUP_PREFIX}.services.payments",
    "cards": f"{GROUP_PREFIX}.services.cards",
    "audit": f"{GROUP_PREFIX}.services.audit",
}


SERVICE_SYMBOL_BY_ROLE: dict[str, str] = {
    "notifications": "#",
    "cards": "*",
    "audit": "-",
}


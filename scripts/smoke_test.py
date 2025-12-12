from __future__ import annotations

import asyncio
from typing import Any

import httpx


SERVICES = {
    "auth": "http://localhost:8001",
    "customers": "http://localhost:8002",
    "accounts": "http://localhost:8003",
    "payments": "http://localhost:8004",
    "cards": "http://localhost:8005",
    "loans": "http://localhost:8006",
    "notifications": "http://localhost:8007",
    "audit": "http://localhost:8008",
}


async def check_health(client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
    response = await client.get(f"{base_url}/health", timeout=10)
    response.raise_for_status()
    return response.json()


async def post_json(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(f"{base_url}{path}", json=payload, timeout=15)
    response.raise_for_status()
    print(response.json())
    return response.json()


async def get_json(client: httpx.AsyncClient, base_url: str, path: str) -> dict[str, Any]:
    response = await client.get(f"{base_url}{path}", timeout=15)
    response.raise_for_status()
    return response.json()


async def run_smoke() -> None:
    async with httpx.AsyncClient() as client:
        results: dict[str, dict[str, Any]] = {}

        results["auth_health"] = await check_health(client, SERVICES["auth"])
        results["auth_event"] = await post_json(
            client,
            SERVICES["auth"],
            "/auth/events",
            {"user_id": "user-1", "action": "login", "ip_address": "127.0.0.1"},
        )

        results["customers_health"] = await check_health(client, SERVICES["customers"])
        results["customers_card"] = await post_json(
            client,
            SERVICES["customers"],
            "/customers/cards",
            {
                "customer_id": "cust-1",
                "product_type": "debit",
                "currency": "RUB",
                "delivery_channel": "branch",
            },
        )

        results["accounts_health"] = await check_health(client, SERVICES["accounts"])
        results["accounts_payment"] = await post_json(
            client,
            SERVICES["accounts"],
            "/accounts/acc-100/payments",
            {
                "from_account": "acc-100",
                "to_account": "acc-200",
                "amount": 2500.5,
                "reference": "invoice-42",
            },
        )

        results["payments_health"] = await check_health(client, SERVICES["payments"])
        results["payments_workload"] = await post_json(
            client,
            SERVICES["payments"],
            "/payments/workload",
            {"symbol": "#", "sleep_seconds": 0, "payload": {"demo": True}},
        )

        results["loans_health"] = await check_health(client, SERVICES["loans"])
        results["loans_application"] = await post_json(
            client,
            SERVICES["loans"],
            "/loans/applications",
            {
                "customer_id": "cust-1",
                "amount": 500_000,
                "term_months": 12,
                "product": "consumer",
            },
        )

        results["cards_health"] = await check_health(client, SERVICES["cards"])
        results["cards_events"] = await get_json(client, SERVICES["cards"], "/cards/events")

        results["notifications_health"] = await check_health(client, SERVICES["notifications"])
        results["notifications_events"] = await get_json(
            client, SERVICES["notifications"], "/notifications/events"
        )

        results["audit_health"] = await check_health(client, SERVICES["audit"])
        results["audit_events"] = await get_json(client, SERVICES["audit"], "/audit/events")

        for name, payload in results.items():
            print(f"{name}: {payload}")


if __name__ == "__main__":
    asyncio.run(run_smoke())


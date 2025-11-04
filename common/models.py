"""Pydantic models shared across microservices."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthEvent(BaseModel):
    """Auth event emitted by the auth-service for notifications and audit."""

    user_id: str
    action: Literal["login", "logout"] = "login"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_service_event(self, source: str) -> dict[str, Any]:
        return {
            "event_id": str(uuid4()),
            "event_type": f"auth.{self.action}",
            "source": source,
            "timestamp": self.created_at.isoformat(),
            "payload": self.model_dump(),
        }


class CardRequest(BaseModel):
    """Card issuance request produced by customers-service."""

    customer_id: str
    product_type: Literal["debit", "credit"] = "debit"
    currency: str = "RUB"
    delivery_channel: Literal["branch", "courier"] = "branch"


class PaymentInstruction(BaseModel):
    """Payment instruction message sent to payments-service."""

    from_account: str
    to_account: str
    amount: float
    currency: str = "RUB"
    reference: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_queue_message(self, source: str) -> dict[str, Any]:
        return {
            "instruction_id": str(uuid4()),
            "source": source,
            "payload": self.model_dump(),
        }


class WorkloadRequest(BaseModel):
    """Generic workload request for fanout/direct/topic routing."""

    symbol: Literal["#", "*", "-"]
    sleep_seconds: int = Field(default=0, ge=0, le=60)
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_message(self, source: str) -> dict[str, Any]:
        return {
            "workload_id": str(uuid4()),
            "symbol": self.symbol,
            "sleep_seconds": self.sleep_seconds,
            "source": source,
            "payload": self.payload,
            "created_at": datetime.utcnow().isoformat(),
        }


class LoanApplication(BaseModel):
    """Loan application data produced by loans-service."""

    customer_id: str
    amount: float
    term_months: int = Field(default=12, ge=1)
    product: Literal["consumer", "mortgage", "auto"] = "consumer"
    currency: str = "RUB"

    def to_workload(self, source: str) -> dict[str, Any]:
        return {
            "workload_id": str(uuid4()),
            "symbol": "-",
            "sleep_seconds": min(int(self.amount // 10_000), 10),
            "source": source,
            "payload": self.model_dump(),
            "created_at": datetime.utcnow().isoformat(),
        }


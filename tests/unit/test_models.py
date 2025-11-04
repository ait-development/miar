from __future__ import annotations

from datetime import datetime

from common.models import AuthEvent, LoanApplication, PaymentInstruction, WorkloadRequest


def test_auth_event_to_service_event_generates_uuid_and_payload() -> None:
    event = AuthEvent(user_id="42", action="login", ip_address="127.0.0.1")

    service_event = event.to_service_event(source="auth-service")

    assert service_event["event_type"] == "auth.login"
    assert service_event["source"] == "auth-service"
    assert service_event["payload"]["user_id"] == "42"
    assert "event_id" in service_event
    assert "timestamp" in service_event


def test_payment_instruction_to_queue_message_embeds_payload() -> None:
    instruction = PaymentInstruction(
        from_account="ACC-1",
        to_account="ACC-2",
        amount=1500.0,
        reference="INV-9",
    )

    message = instruction.to_queue_message(source="accounts-service")

    assert message["source"] == "accounts-service"
    assert message["payload"]["to_account"] == "ACC-2"
    assert "instruction_id" in message


def test_workload_request_to_message_sets_created_at() -> None:
    request = WorkloadRequest(symbol="#", sleep_seconds=2, payload={"foo": "bar"})

    message = request.to_message(source="payments-service")

    assert message["symbol"] == "#"
    assert message["sleep_seconds"] == 2
    assert message["payload"] == {"foo": "bar"}
    assert datetime.fromisoformat(message["created_at"])  # raises if invalid


def test_loan_application_to_workload_uses_symbol_minus() -> None:
    application = LoanApplication(customer_id="CUST-100", amount=200_000, term_months=24)

    workload = application.to_workload(source="loans-service")

    assert workload["symbol"] == "-"
    assert workload["source"] == "loans-service"
    assert workload["payload"]["customer_id"] == "CUST-100"


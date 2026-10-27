"""End-to-end-Webhook mit echtem Stripe-SDK (Signaturprüfung, kein Netzwerk).

Die übrigen Webhook-Tests mocken ``construct_event`` mit Plain-dicts. Dieser Test
prüft, dass das echte SDK-Event (ab stripe 15 kein dict mehr) im Handler ankommt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.core.config.settings import Settings
from backend.features.billing.stripe_service import StripeService
from backend.features.billing.stripe_webhook import StripeWebhookHandler
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)

_SECRET = "whsec_test_secret"


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "STRIPE_ENABLED": True,
            "STRIPE_SECRET_KEY": "sk_test_x",
            "STRIPE_WEBHOOK_SECRET": _SECRET,
            "STRIPE_PRICE_STANDARD": "price_std",
            "STRIPE_PRICE_PRO": "price_pro",
            "STRIPE_PRICE_BUSINESS": "price_biz",
        }
    )


def _signed(event: dict[str, object]) -> tuple[bytes, str]:
    payload = json.dumps(event).encode("utf-8")
    ts = int(time.time())
    signed = f"{ts}.{payload.decode('utf-8')}".encode()
    sig = hmac.new(_SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return payload, f"t={ts},v1={sig}"


def _event() -> dict[str, object]:
    start = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp())
    return {
        "id": "evt_1",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_1",
                "object": "subscription",
                "customer": "cus_1",
                "status": "active",
                "metadata": {"account_id": "x"},
                "items": {
                    "object": "list",
                    "data": [
                        {
                            "id": "si_1",
                            "object": "subscription_item",
                            "price": {"id": "price_pro", "object": "price"},
                            "current_period_start": start,
                            "current_period_end": end,
                        }
                    ],
                },
            }
        },
    }


def test_construct_event_returns_plain_dict() -> None:
    svc = StripeService(_settings(), MagicMock(), MagicMock(), MagicMock())
    payload, header = _signed(_event())
    event = svc.construct_event(payload, header)
    assert isinstance(event, dict)
    assert event["type"] == "customer.subscription.updated"
    assert isinstance(event["data"]["object"]["items"]["data"][0], dict)


def test_signed_subscription_event_updates_plan(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")
    settings = _settings()
    svc = StripeService(settings, subs, accounts, MagicMock())
    handler = StripeWebhookHandler(settings, subs, svc)

    payload, header = _signed(_event())
    handler.handle(payload, header)

    updated = subs.get_by_account(account.id)
    assert updated is not None
    assert updated.plan_id == "pro"
    assert updated.status == "active"
    assert updated.stripe_subscription_id == "sub_1"
    assert updated.current_period_end == datetime(2026, 2, 1, tzinfo=UTC)

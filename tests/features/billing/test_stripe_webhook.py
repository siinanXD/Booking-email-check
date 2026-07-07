"""Tests für Stripe-Webhook-Handler."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.core.config.settings import Settings
from backend.features.billing.stripe_webhook import StripeWebhookHandler
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "STRIPE_PRICE_STANDARD": "price_std",
            "STRIPE_PRICE_PRO": "price_pro",
            "STRIPE_PRICE_BUSINESS": "price_biz",
        }
    )


def _stripe_sub(
    *,
    customer: str = "cus_1",
    price_id: str = "price_std",
    status: str = "active",
) -> dict[str, object]:
    now = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp())
    return {
        "id": "sub_1",
        "customer": customer,
        "status": status,
        "current_period_start": now,
        "current_period_end": end,
        "items": {"data": [{"price": {"id": price_id}}]},
    }


def test_subscription_updated_maps_plan(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")

    stripe_svc = MagicMock()
    stripe_svc.construct_event.return_value = {
        "type": "customer.subscription.updated",
        "data": {"object": _stripe_sub()},
    }
    handler = StripeWebhookHandler(_settings(), subs, stripe_svc)
    handler.handle(b"{}", "sig")

    updated = subs.get_by_account(account.id)
    assert updated is not None
    assert updated.plan_id == "standard"
    assert updated.status == "active"
    assert updated.stripe_subscription_id == "sub_1"


def test_subscription_deleted_sets_canceled(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")
    subs.apply_stripe_subscription(
        account.id,
        plan_id="standard",
        status="active",
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2026, 2, 1, tzinfo=UTC),
        subscription_id="sub_1",
    )

    stripe_svc = MagicMock()
    stripe_svc.construct_event.return_value = {
        "type": "customer.subscription.deleted",
        "data": {"object": _stripe_sub(status="canceled")},
    }
    handler = StripeWebhookHandler(_settings(), subs, stripe_svc)
    handler.handle(b"{}", "sig")

    updated = subs.get_by_account(account.id)
    assert updated is not None
    assert updated.status == "canceled"


def test_incomplete_subscription_event_is_ignored(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")

    stripe_svc = MagicMock()
    stripe_svc.construct_event.return_value = {
        "type": "customer.subscription.created",
        "data": {"object": _stripe_sub(status="incomplete")},
    }
    handler = StripeWebhookHandler(_settings(), subs, stripe_svc)
    handler.handle(b"{}", "sig")

    unchanged = subs.get_by_account(account.id)
    assert unchanged is not None
    assert unchanged.status == "trialing"
    assert unchanged.plan_id == "trial"


def test_period_bounds_from_item_level_fields(mock_db: object) -> None:
    """Stripe-API 2025-03 (Basil): current_period_* liegt auf Item-Ebene."""
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")

    start = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp())
    basil_sub = {
        "id": "sub_1",
        "customer": "cus_1",
        "status": "active",
        "items": {
            "data": [
                {
                    "price": {"id": "price_std"},
                    "current_period_start": start,
                    "current_period_end": end,
                }
            ]
        },
    }
    stripe_svc = MagicMock()
    stripe_svc.construct_event.return_value = {
        "type": "customer.subscription.updated",
        "data": {"object": basil_sub},
    }
    handler = StripeWebhookHandler(_settings(), subs, stripe_svc)
    handler.handle(b"{}", "sig")

    updated = subs.get_by_account(account.id)
    assert updated is not None
    assert updated.current_period_end == datetime(2026, 2, 1, tzinfo=UTC)
    assert updated.current_period_start == datetime(2026, 1, 1, tzinfo=UTC)


def test_payment_failed_sets_past_due(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.set_stripe_ids(account.id, customer_id="cus_1")

    stripe_svc = MagicMock()
    stripe_svc.construct_event.return_value = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_1"}},
    }
    handler = StripeWebhookHandler(_settings(), subs, stripe_svc)
    handler.handle(b"{}", "sig")

    updated = subs.get_by_account(account.id)
    assert updated is not None
    assert updated.status == "past_due"

"""Tests für StripeService (gemocktes SDK)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.core.config.settings import Settings
from backend.features.billing.stripe_service import StripeBillingError, StripeService
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "OPENAI_API_KEY": "sk-test",
        "MONGODB_URI": "mongodb://localhost",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "STRIPE_ENABLED": True,
        "STRIPE_SECRET_KEY": "sk_test_x",
        "STRIPE_PRICE_STANDARD": "price_std",
        "STRIPE_PRICE_PRO": "price_pro",
        "STRIPE_PRICE_BUSINESS": "price_biz",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_ensure_customer_idempotent(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    users = UserRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    users.create(
        email="tenant@test.local",
        password_hash="x",
        role="owner",
        account_id=account.id,
    )
    subs.create_trial(account.id)

    svc = StripeService(_settings(), subs, accounts, users)
    with patch("backend.features.billing.stripe_service.stripe") as mock_stripe:
        mock_stripe.Customer.create.return_value = {"id": "cus_123"}
        first = svc.ensure_customer(account.id)
        second = svc.ensure_customer(account.id)
    assert first == "cus_123"
    assert second == "cus_123"
    mock_stripe.Customer.create.assert_called_once()


def test_create_checkout_session_rejects_trial(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    users = UserRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    svc = StripeService(_settings(), subs, accounts, users)
    with pytest.raises(StripeBillingError):
        svc.create_checkout_session(account.id, "trial")


def test_create_checkout_session_returns_url(mock_db: object) -> None:
    accounts = AccountRepository(mock_db)
    users = UserRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    svc = StripeService(_settings(), subs, accounts, users)
    with patch("backend.features.billing.stripe_service.stripe") as mock_stripe:
        mock_stripe.Customer.create.return_value = {"id": "cus_123"}
        mock_stripe.checkout.Session.create.return_value = {
            "url": "https://checkout.stripe.test/session"
        }
        url = svc.create_checkout_session(account.id, "standard")
    assert url == "https://checkout.stripe.test/session"
    mock_stripe.checkout.Session.create.assert_called_once()
    call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs["client_reference_id"] == account.id


def test_create_checkout_rejects_existing_active_subscription(
    mock_db: object,
) -> None:
    from datetime import UTC, datetime, timedelta

    accounts = AccountRepository(mock_db)
    users = UserRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    subs.apply_stripe_subscription(
        account.id,
        plan_id="standard",
        status="active",
        period_start=datetime.now(UTC),
        period_end=datetime.now(UTC) + timedelta(days=30),
        customer_id="cus_123",
        subscription_id="sub_123",
    )
    svc = StripeService(_settings(), subs, accounts, users)
    with pytest.raises(StripeBillingError, match="Kundenportal"):
        svc.create_checkout_session(account.id, "pro")


def test_create_checkout_allowed_after_cancellation(mock_db: object) -> None:
    from datetime import UTC, datetime, timedelta

    accounts = AccountRepository(mock_db)
    users = UserRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    users.create(
        email="tenant@test.local",
        password_hash="x",
        role="owner",
        account_id=account.id,
    )
    subs.create_trial(account.id)
    subs.apply_stripe_subscription(
        account.id,
        plan_id="standard",
        status="active",
        period_start=datetime.now(UTC),
        period_end=datetime.now(UTC) + timedelta(days=30),
        customer_id="cus_123",
        subscription_id="sub_123",
    )
    subs.set_status(account.id, "canceled")
    svc = StripeService(_settings(), subs, accounts, users)
    with patch("backend.features.billing.stripe_service.stripe") as mock_stripe:
        mock_stripe.checkout.Session.create.return_value = {
            "url": "https://checkout.stripe.test/session"
        }
        url = svc.create_checkout_session(account.id, "standard")
    assert url == "https://checkout.stripe.test/session"


def test_construct_event_invalid_signature() -> None:
    svc = StripeService(
        _settings(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    with patch("backend.features.billing.stripe_service.stripe") as mock_stripe:
        mock_stripe.Webhook.construct_event.side_effect = ValueError("bad sig")
        with pytest.raises(StripeBillingError):
            svc.construct_event(b"{}", "sig")

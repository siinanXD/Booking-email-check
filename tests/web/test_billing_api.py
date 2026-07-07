"""Web-API-Tests für Billing."""

from __future__ import annotations

from backend.core.models.entities import Property
from backend.features.booking.entity_sync import _property_id
from backend.infrastructure.repositories.property_repository import PropertyRepository


def test_trial_on_approve_not_on_register(
    mock_db: object, client: object, auth_headers: dict
) -> None:
    from backend.infrastructure.repositories.subscription_repository import (
        SubscriptionRepository,
    )
    from tests.web.test_registration import _register_payload

    subs = SubscriptionRepository(mock_db)
    payload = _register_payload(email="trial-on-approve@test.local")
    client.post("/api/auth/register", json=payload)
    pending = client.get("/api/admin/accounts?status=pending", headers=auth_headers)
    account_id = pending.get_json()["items"][0]["id"]
    assert subs.get_by_account(account_id) is None
    client.post(f"/api/admin/accounts/{account_id}/approve", headers=auth_headers)
    sub = subs.get_by_account(account_id)
    assert sub is not None
    assert sub.plan_id == "trial"
    assert sub.status == "trialing"


def test_property_create_403_at_limit(
    app: object, client: object, tenant_owner_auth_headers: dict
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    ctx.settings.billing_enforcement_enabled = True
    account_id = ctx.user_repo.get_by_email("owner-mail@test.local").account_id
    assert account_id
    subs = ctx.subscription_repo
    subs.set_overrides(account_id, override_max_properties=1)
    PropertyRepository(ctx.db).upsert(
        Property(
            property_id=_property_id(account_id, "Existing"),
            name="Existing",
            account_id=account_id,
        ),
        account_id=account_id,
    )
    resp = client.post(
        "/api/properties",
        json={"name": "New One"},
        headers=tenant_owner_auth_headers,
    )
    assert resp.status_code == 403
    assert resp.get_json()["code"] == "plan_limit_reached"


def test_billing_plans_excludes_legacy(client: object) -> None:
    resp = client.get("/api/billing/plans")
    assert resp.status_code == 200
    ids = {item["plan_id"] for item in resp.get_json()["items"]}
    assert "legacy" not in ids
    assert "standard" in ids


def test_billing_subscription_returns_numbers(
    app: object, client: object, tenant_owner_auth_headers: dict
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    account_id = ctx.user_repo.get_by_email("owner-mail@test.local").account_id
    assert account_id
    assert ctx.subscription_repo.get_by_account(account_id) is not None
    resp = client.get("/api/billing/subscription", headers=tenant_owner_auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["plan_id"] == "trial"
    assert "mails_used" in body
    assert "properties_limit" in body
    assert body["self_service"] is False


def test_billing_checkout_disabled_without_stripe(
    client: object, tenant_owner_auth_headers: dict
) -> None:
    resp = client.post(
        "/api/billing/checkout",
        json={"plan_id": "standard"},
        headers=tenant_owner_auth_headers,
    )
    assert resp.status_code == 503


def test_billing_portal_disabled_without_stripe(
    client: object, tenant_owner_auth_headers: dict
) -> None:
    resp = client.post("/api/billing/portal", headers=tenant_owner_auth_headers)
    assert resp.status_code == 503


def test_billing_webhook_disabled_without_stripe(client: object) -> None:
    resp = client.post("/api/billing/webhook", data=b"{}")
    assert resp.status_code == 503


def test_billing_checkout_with_mock_stripe(
    app: object, client: object, tenant_owner_auth_headers: dict
) -> None:
    from unittest.mock import MagicMock

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    mock_svc = MagicMock()
    mock_svc.enabled = True
    mock_svc.create_checkout_session.return_value = "https://checkout.test/url"
    ctx.stripe_service = mock_svc
    resp = client.post(
        "/api/billing/checkout",
        json={"plan_id": "standard"},
        headers=tenant_owner_auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["url"] == "https://checkout.test/url"


def test_billing_subscription_self_service_flag(
    app: object, client: object, tenant_owner_auth_headers: dict
) -> None:
    from unittest.mock import MagicMock

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    mock_svc = MagicMock()
    mock_svc.enabled = True
    ctx.stripe_service = mock_svc
    resp = client.get("/api/billing/subscription", headers=tenant_owner_auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["self_service"] is True

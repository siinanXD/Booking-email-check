"""Tenant-Billing-API."""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.rate_limit import limiter
from backend.api.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanCatalogItem,
    PlanCatalogResponse,
    PortalResponse,
    SubscriptionResponse,
)
from backend.features.billing.plans import public_plans
from backend.features.billing.stripe_service import StripeBillingError

logger = logging.getLogger(__name__)

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _self_service_enabled() -> bool:
    svc = getattr(g.ctx, "stripe_service", None)
    return svc is not None and svc.enabled


def _subscription_payload(account_id: str) -> SubscriptionResponse:
    svc = g.ctx.entitlement_service
    assert svc is not None
    sub = g.ctx.subscription_repo.get_by_account(account_id)
    plan = svc.plan_for(account_id)
    usage = svc.usage_snapshot(account_id)
    period_end = sub.current_period_end.isoformat() if sub else ""
    quota_start = sub.quota_window_start.isoformat() if sub else ""
    status = sub.status if sub else "trialing"
    return SubscriptionResponse(
        plan_id=plan.plan_id,
        plan_name=plan.display_name,
        status=status,
        period_end=period_end,
        quota_window_start=quota_start,
        mails_used=usage["mails_used"],
        mails_limit=usage["mails_limit"],
        properties_used=usage["properties_used"],
        properties_limit=usage["properties_limit"],
        users_used=usage["users_used"],
        users_limit=usage["users_limit"],
        mailboxes_limit=usage["mailboxes_limit"],
        effective_features=sorted(svc.effective_features(account_id)),
        self_service=_self_service_enabled(),
    )


@billing_bp.get("/plans")
def list_plans() -> tuple[Any, int]:
    """Öffentlicher Plan-Katalog (ohne Legacy)."""
    items = [
        PlanCatalogItem(
            plan_id=plan.plan_id,
            display_name=plan.display_name,
            price_eur_monthly=plan.price_eur_monthly,
            price_eur_yearly=plan.price_eur_monthly * 10,
            monthly_mail_quota=plan.monthly_mail_quota,
            max_properties=plan.max_properties,
            max_users=plan.max_users,
            max_mailboxes=plan.max_mailboxes,
            features=sorted(plan.features),
        )
        for plan in public_plans()
    ]
    return jsonify(PlanCatalogResponse(items=items).model_dump()), 200


@billing_bp.get("/subscription")
@require_auth
@require_account
def get_subscription() -> tuple[Any, int]:
    """Aktuelles Abo und Verbrauch des Mandanten."""
    account_id = get_request_account_id()
    assert account_id
    if g.ctx.entitlement_service is None:
        return jsonify({"error": "Billing nicht verfügbar", "code": 503}), 503
    return jsonify(_subscription_payload(account_id).model_dump()), 200


@billing_bp.post("/checkout")
@require_auth
@require_account
def create_checkout() -> tuple[Any, int]:
    """Stripe Checkout für Plan-Upgrade starten."""
    stripe_svc = getattr(g.ctx, "stripe_service", None)
    if stripe_svc is None or not stripe_svc.enabled:
        return jsonify({"error": "Stripe nicht verfügbar", "code": 503}), 503
    account_id = get_request_account_id()
    assert account_id
    body = CheckoutRequest.model_validate(request.get_json(silent=True) or {})
    try:
        url = stripe_svc.create_checkout_session(account_id, body.plan_id)
    except StripeBillingError as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify(CheckoutResponse(url=url).model_dump()), 200


@billing_bp.post("/portal")
@require_auth
@require_account
def create_portal() -> tuple[Any, int]:
    """Stripe Customer Portal öffnen (Plan ändern / kündigen)."""
    stripe_svc = getattr(g.ctx, "stripe_service", None)
    if stripe_svc is None or not stripe_svc.enabled:
        return jsonify({"error": "Stripe nicht verfügbar", "code": 503}), 503
    account_id = get_request_account_id()
    assert account_id
    try:
        url = stripe_svc.create_portal_session(account_id)
    except StripeBillingError as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify(PortalResponse(url=url).model_dump()), 200


@billing_bp.post("/webhook")
@limiter.exempt
def stripe_webhook() -> tuple[Any, int]:
    """Stripe-Webhook (ohne Auth, Signaturpflicht)."""
    handler = getattr(g.ctx, "stripe_webhook_handler", None)
    if handler is None:
        return jsonify({"error": "Stripe nicht verfügbar", "code": 503}), 503
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        handler.handle(request.get_data(), sig_header)
    except StripeBillingError as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    except Exception:
        logger.exception("Stripe webhook processing failed")
        return (
            jsonify({"error": "Webhook-Verarbeitung fehlgeschlagen", "code": 500}),
            500,
        )
    return jsonify({"received": True}), 200

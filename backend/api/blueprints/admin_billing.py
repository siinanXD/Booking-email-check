"""Plattform-Admin: Abo-Verwaltung."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from flask import g, jsonify, request

from backend.api.blueprints.admin import admin_bp
from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.schemas.billing import (
    AdminSubscriptionExtendTrialRequest,
    AdminSubscriptionOverridesRequest,
    AdminSubscriptionSetRequest,
    SubscriptionResponse,
)
from backend.features.billing.plans import PLANS


def _actor_id() -> str | None:
    current = getattr(g, "current_user", None)
    return current.get("id") if isinstance(current, dict) else None


def _audit(action: str, **details: Any) -> None:
    g.ctx.admin_audit_log_repo.append(action, user_id=_actor_id(), details=details)


def _subscription_response(account_id: str) -> SubscriptionResponse:
    svc = g.ctx.entitlement_service
    assert svc is not None
    sub = g.ctx.subscription_repo.get_by_account(account_id)
    plan = svc.plan_for(account_id)
    usage = svc.usage_snapshot(account_id)
    return SubscriptionResponse(
        plan_id=plan.plan_id,
        plan_name=plan.display_name,
        status=sub.status if sub else "trialing",
        period_end=sub.current_period_end.isoformat() if sub else "",
        quota_window_start=sub.quota_window_start.isoformat() if sub else "",
        mails_used=usage["mails_used"],
        mails_limit=usage["mails_limit"],
        properties_used=usage["properties_used"],
        properties_limit=usage["properties_limit"],
        users_used=usage["users_used"],
        users_limit=usage["users_limit"],
        mailboxes_limit=usage["mailboxes_limit"],
        effective_features=sorted(svc.effective_features(account_id)),
    )


@admin_bp.get("/accounts/<account_id>/subscription")
@require_auth
@require_platform_admin
def get_account_subscription(account_id: str) -> tuple[Any, int]:
    """Lädt Abo und Verbrauch eines Mandanten."""
    if g.ctx.account_repo.get_by_id(account_id) is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return jsonify(_subscription_response(account_id).model_dump()), 200


@admin_bp.put("/accounts/<account_id>/subscription")
@require_auth
@require_platform_admin
def set_account_subscription(account_id: str) -> tuple[Any, int]:
    """Setzt Plan und Abo-Periode; entfernt expires_at."""
    if g.ctx.account_repo.get_by_id(account_id) is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    body = AdminSubscriptionSetRequest.model_validate(
        request.get_json(silent=True) or {}
    )
    if body.plan_id not in PLANS:
        return jsonify({"error": "Unbekannter Plan", "code": 400}), 400
    now = datetime.now(UTC)
    if body.period_end:
        try:
            period_end = datetime.fromisoformat(body.period_end).astimezone(UTC)
        except ValueError:
            return jsonify({"error": "Ungültiges Datumsformat", "code": 400}), 400
    else:
        period_end = now + timedelta(days=30)
    sub = g.ctx.subscription_repo.get_by_account(account_id)
    if sub is None:
        if body.plan_id == "legacy":
            g.ctx.subscription_repo.create_legacy(account_id)
        else:
            g.ctx.subscription_repo.create_trial(account_id)
    updated = g.ctx.subscription_repo.set_plan(account_id, body.plan_id, period_end)
    if updated is None:
        return jsonify({"error": "Subscription update failed", "code": 500}), 500
    g.ctx.account_repo.set_expiry(account_id, None)
    _audit(
        "subscription.set_plan",
        account_id=account_id,
        plan_id=body.plan_id,
        period_end=period_end.isoformat(),
    )
    return jsonify(_subscription_response(account_id).model_dump()), 200


@admin_bp.post("/accounts/<account_id>/subscription/extend-trial")
@require_auth
@require_platform_admin
def extend_account_trial(account_id: str) -> tuple[Any, int]:
    """Verlängert Trial um N Tage."""
    if g.ctx.account_repo.get_by_id(account_id) is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    body = AdminSubscriptionExtendTrialRequest.model_validate(
        request.get_json(silent=True) or {}
    )
    sub = g.ctx.subscription_repo.get_by_account(account_id)
    if sub is None:
        g.ctx.subscription_repo.create_trial(account_id)
    updated = g.ctx.subscription_repo.extend_trial(account_id, body.days)
    if updated is None:
        return jsonify({"error": "Trial extension failed", "code": 500}), 500
    _audit(
        "subscription.extend_trial",
        account_id=account_id,
        days=body.days,
        period_end=updated.current_period_end.isoformat(),
    )
    return jsonify(_subscription_response(account_id).model_dump()), 200


@admin_bp.put("/accounts/<account_id>/subscription/overrides")
@require_auth
@require_platform_admin
def set_subscription_overrides(account_id: str) -> tuple[Any, int]:
    """Setzt Limit-Overrides für Sonderdeals."""
    if g.ctx.account_repo.get_by_id(account_id) is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    body = AdminSubscriptionOverridesRequest.model_validate(
        request.get_json(silent=True) or {}
    )
    if g.ctx.subscription_repo.get_by_account(account_id) is None:
        g.ctx.subscription_repo.create_trial(account_id)
    updated = g.ctx.subscription_repo.set_overrides(
        account_id,
        override_max_mails=body.override_max_mails,
        override_max_properties=body.override_max_properties,
        override_max_users=body.override_max_users,
        clear_unset=True,
    )
    if updated is None:
        return jsonify({"error": "Override update failed", "code": 500}), 500
    _audit(
        "subscription.overrides",
        account_id=account_id,
        override_max_mails=body.override_max_mails,
        override_max_properties=body.override_max_properties,
        override_max_users=body.override_max_users,
    )
    return jsonify(_subscription_response(account_id).model_dump()), 200

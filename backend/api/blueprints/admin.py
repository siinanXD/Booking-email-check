"""Plattform-Admin: Account-Freischaltung."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.schemas.accounts import (
    AccountActionResponse,
    AccountListItem,
    AccountListResponse,
    AccountRejectRequest,
    AdminMeResponse,
)
from backend.api.schemas.admin_diagnostics import AdminWhatsAppTestRequest
from backend.api.services.admin_diagnostics_service import (
    AccountNotFoundError,
    AdminDiagnosticsService,
    RateLimitExceededError,
)
from backend.api.services.admin_overview_queries import (
    admin_account_detail,
    admin_costs_metrics,
    admin_overview,
    admin_public_config,
    admin_tokens_metrics,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _diagnostics() -> AdminDiagnosticsService:
    return AdminDiagnosticsService(g.ctx, g.settings)


@admin_bp.get("/me")
@require_auth
@require_platform_admin
def admin_me() -> tuple[Any, int]:
    """Plattform-Admin-Profil (ohne Mail-Onboarding-Pflicht)."""
    from backend.infrastructure.repositories.user_repository import UserRecord

    user_payload = g.current_user
    user_id = user_payload.get("id")
    if not isinstance(user_id, str):
        return jsonify({"error": "Unauthorized", "code": 401}), 401
    user = g.ctx.user_repo.get_by_id(user_id)
    if user is None or not isinstance(user, UserRecord):
        return jsonify({"error": "Unauthorized", "code": 401}), 401
    return (
        jsonify(
            AdminMeResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                account_id=user.account_id,
                mail_onboarding_required=False,
            ).model_dump()
        ),
        200,
    )


def _to_list_item(account: object) -> AccountListItem:
    from backend.infrastructure.repositories.account_repository import AccountRecord

    assert isinstance(account, AccountRecord)
    created = account.created_at.isoformat()
    return AccountListItem(
        id=account.id,
        display_name=account.display_name,
        contact_email=account.contact_email,
        account_type=account.account_type,
        company_name=account.company_name,
        phone=account.phone,
        status=account.status,
        rejection_reason=account.rejection_reason,
        created_at=created,
    )


@admin_bp.get("/accounts")
@require_auth
@require_platform_admin
def list_accounts() -> tuple[Any, int]:
    """Listet Accounts (Metadaten) – Filter: status=pending|active|..."""
    status = request.args.get("status")
    if status:
        accounts = g.ctx.account_repo.list_by_status(status)
    else:
        accounts = g.ctx.account_repo.list_by_status(None)
    items = [_to_list_item(a) for a in accounts]
    return (
        jsonify(AccountListResponse(items=items, total=len(items)).model_dump()),
        200,
    )


@admin_bp.post("/accounts/<account_id>/approve")
@require_auth
@require_platform_admin
def approve_account(account_id: str) -> tuple[Any, int]:
    """Schaltet einen Account frei."""
    account = g.ctx.account_repo.get_by_id(account_id)
    if account is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    if account.status == "active":
        return (
            jsonify(
                AccountActionResponse(
                    id=account_id,
                    status="active",
                    message="Account ist bereits freigeschaltet.",
                ).model_dump()
            ),
            200,
        )
    updated = g.ctx.account_repo.update_status(account_id, "active")
    if updated is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return (
        jsonify(
            AccountActionResponse(
                id=account_id,
                status="active",
                message="Account freigeschaltet.",
            ).model_dump()
        ),
        200,
    )


@admin_bp.post("/accounts/<account_id>/reject")
@require_auth
@require_platform_admin
def reject_account(account_id: str) -> tuple[Any, int]:
    """Lehnt einen Account ab."""
    account = g.ctx.account_repo.get_by_id(account_id)
    if account is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    body = AccountRejectRequest.model_validate(request.get_json(silent=True) or {})
    updated = g.ctx.account_repo.update_status(
        account_id,
        "rejected",
        rejection_reason=body.reason,
    )
    if updated is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return (
        jsonify(
            AccountActionResponse(
                id=account_id,
                status="rejected",
                message="Account abgelehnt.",
            ).model_dump()
        ),
        200,
    )


@admin_bp.get("/accounts/<account_id>/mail/connection")
@require_auth
@require_platform_admin
def admin_get_mail_connection(account_id: str) -> tuple[Any, int]:
    """Postfach-Status eines Mandanten (read-only)."""
    try:
        connection = _diagnostics().get_mail_connection(account_id)
    except AccountNotFoundError:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return jsonify(connection.model_dump()), 200


@admin_bp.post("/accounts/<account_id>/mail/test")
@require_auth
@require_platform_admin
def admin_test_mail_connection(account_id: str) -> tuple[Any, int]:
    """Testet die Postfach-Verbindung eines Mandanten."""
    try:
        result = _diagnostics().test_mail_connection(account_id)
    except AccountNotFoundError:
        return jsonify({"error": "Account not found", "code": 404}), 404
    except RateLimitExceededError:
        return (
            jsonify(
                {
                    "error": "Zu viele Tests — bitte eine Minute warten.",
                    "code": 429,
                }
            ),
            429,
        )
    return jsonify(result.model_dump()), 200


@admin_bp.get("/accounts/<account_id>/whatsapp")
@require_auth
@require_platform_admin
def admin_get_whatsapp_info(account_id: str) -> tuple[Any, int]:
    """WhatsApp-Konfiguration eines Mandanten (ohne Secrets)."""
    try:
        info = _diagnostics().get_whatsapp_info(account_id)
    except AccountNotFoundError:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return jsonify(info.model_dump()), 200


@admin_bp.post("/accounts/<account_id>/whatsapp/test")
@require_auth
@require_platform_admin
def admin_test_whatsapp(account_id: str) -> tuple[Any, int]:
    """WhatsApp-Testversand für einen Mandanten."""
    body = AdminWhatsAppTestRequest.model_validate(request.get_json(silent=True) or {})
    try:
        result = _diagnostics().test_whatsapp(account_id, body)
    except AccountNotFoundError:
        return jsonify({"error": "Account not found", "code": 404}), 404
    except RateLimitExceededError:
        return (
            jsonify(
                {
                    "error": "Zu viele Tests — bitte eine Minute warten.",
                    "code": 429,
                }
            ),
            429,
        )
    return jsonify(result.model_dump()), 200


def _parse_days(default: int = 30) -> int:
    raw = request.args.get("days", str(default))
    try:
        days = int(raw)
    except ValueError:
        days = default
    return max(1, min(days, 365))


@admin_bp.get("/overview")
@require_auth
@require_platform_admin
def admin_overview_route() -> tuple[Any, int]:
    """Plattform-KPIs und Mandanten-Aktivität."""
    data = admin_overview(g.ctx, days=_parse_days(30))
    return jsonify(data.model_dump()), 200


@admin_bp.get("/accounts/<account_id>/detail")
@require_auth
@require_platform_admin
def admin_account_detail_route(account_id: str) -> tuple[Any, int]:
    """Mandanten-Drill-down inkl. DB-Counts."""
    detail = admin_account_detail(g.ctx, account_id, g.settings, days=_parse_days(30))
    if detail is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    return jsonify(detail.model_dump()), 200


@admin_bp.get("/metrics/costs")
@require_auth
@require_platform_admin
def admin_metrics_costs() -> tuple[Any, int]:
    """Cross-Tenant Kosten und Top-Mails."""
    data = admin_costs_metrics(g.ctx, g.settings, days=_parse_days(30))
    return jsonify(data.model_dump()), 200


@admin_bp.get("/metrics/tokens")
@require_auth
@require_platform_admin
def admin_metrics_tokens() -> tuple[Any, int]:
    """Cross-Tenant Token-Aggregation."""
    data = admin_tokens_metrics(g.ctx, days=_parse_days(30))
    return jsonify(data.model_dump()), 200


@admin_bp.get("/config/public")
@require_auth
@require_platform_admin
def admin_config_public() -> tuple[Any, int]:
    """Nicht-sensitive Konfiguration für Admin-UI."""
    data = admin_public_config(g.settings)
    return jsonify(data.model_dump()), 200


import backend.api.blueprints.admin_account_workflows  # noqa: E402, F401
import backend.api.blueprints.admin_llm_routes  # noqa: E402, F401

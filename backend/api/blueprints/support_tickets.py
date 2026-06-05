"""Support-Tickets: Mandant + Plattform-Admin."""

from __future__ import annotations

from typing import Any, cast

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.support_ticket import (
    AdminSupportTicketPatchRequest,
    PlatformAdminConfigUpdateRequest,
    SupportTicketCreateRequest,
)
from backend.api.services.support_ticket_service import (
    RateLimitExceededError,
    SupportTicketNotFoundError,
    create_ticket,
    get_admin_ticket,
    get_platform_admin_config,
    list_admin_tickets,
    list_tenant_tickets,
    patch_admin_ticket,
    retry_whatsapp,
    update_platform_admin_config,
)
from backend.core.models.support_ticket import SupportTicketStatus, SupportTicketUrgency

support_bp = Blueprint("support", __name__, url_prefix="/api/support")
admin_support_bp = Blueprint(
    "admin_support",
    __name__,
    url_prefix="/api/admin/support",
)


@support_bp.post("/tickets")
@require_auth
@require_account
def tenant_create_ticket() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    try:
        body = SupportTicketCreateRequest.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as exc:
        return jsonify({"error": exc.errors()[0]["msg"], "code": 400}), 400

    user = g.current_user
    user_id = str(user.get("id", ""))
    user_email = str(user.get("email", ""))
    try:
        ticket = create_ticket(
            g.ctx,
            g.settings,
            account_id=account_id,
            user_id=user_id,
            user_email=user_email,
            body=body,
        )
    except RateLimitExceededError:
        return (
            jsonify({"error": "Zu viele Tickets — bitte später erneut", "code": 429}),
            429,
        )
    return jsonify(ticket.model_dump()), 201


@support_bp.get("/tickets")
@require_auth
@require_account
def tenant_list_tickets() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    result = list_tenant_tickets(g.ctx, account_id, limit=limit)
    return jsonify(result.model_dump()), 200


@admin_support_bp.get("/tickets")
@require_auth
@require_platform_admin
def admin_list_tickets() -> tuple[Any, int]:
    status_raw = request.args.get("status")
    urgency_raw = request.args.get("urgency")
    account_id = (request.args.get("account_id") or "").strip() or None
    limit = min(max(int(request.args.get("limit", 100)), 1), 200)
    status: SupportTicketStatus | None = None
    urgency: SupportTicketUrgency | None = None
    if status_raw in ("open", "in_progress", "resolved", "closed"):
        status = cast(SupportTicketStatus, status_raw)
    if urgency_raw in ("low", "normal", "high", "critical"):
        urgency = cast(SupportTicketUrgency, urgency_raw)
    result = list_admin_tickets(
        g.ctx,
        status=status,
        urgency=urgency,
        account_id=account_id,
        limit=limit,
    )
    return jsonify(result.model_dump()), 200


@admin_support_bp.get("/tickets/<ticket_id>")
@require_auth
@require_platform_admin
def admin_get_ticket(ticket_id: str) -> tuple[Any, int]:
    try:
        ticket = get_admin_ticket(g.ctx, ticket_id)
    except SupportTicketNotFoundError:
        return jsonify({"error": "Ticket nicht gefunden", "code": 404}), 404
    return jsonify(ticket.model_dump()), 200


@admin_support_bp.patch("/tickets/<ticket_id>")
@require_auth
@require_platform_admin
def admin_patch_ticket(ticket_id: str) -> tuple[Any, int]:
    try:
        body = AdminSupportTicketPatchRequest.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as exc:
        return jsonify({"error": exc.errors()[0]["msg"], "code": 400}), 400
    try:
        ticket = patch_admin_ticket(
            g.ctx,
            ticket_id,
            status=body.status,
            admin_note=body.admin_note,
        )
    except SupportTicketNotFoundError:
        return jsonify({"error": "Ticket nicht gefunden", "code": 404}), 404
    return jsonify(ticket.model_dump()), 200


@admin_support_bp.post("/tickets/<ticket_id>/retry-whatsapp")
@require_auth
@require_platform_admin
def admin_retry_whatsapp(ticket_id: str) -> tuple[Any, int]:
    try:
        ticket = retry_whatsapp(g.ctx, g.settings, ticket_id)
    except SupportTicketNotFoundError:
        return jsonify({"error": "Ticket nicht gefunden", "code": 404}), 404
    return jsonify(ticket.model_dump()), 200


@admin_support_bp.get("/config")
@require_auth
@require_platform_admin
def admin_get_support_config() -> tuple[Any, int]:
    config = get_platform_admin_config(g.ctx, g.settings)
    return jsonify(config.model_dump()), 200


@admin_support_bp.put("/config")
@require_auth
@require_platform_admin
def admin_put_support_config() -> tuple[Any, int]:
    try:
        body = PlatformAdminConfigUpdateRequest.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as exc:
        return jsonify({"error": exc.errors()[0]["msg"], "code": 400}), 400
    user_id = str(g.current_user.get("id", ""))
    try:
        config = update_platform_admin_config(g.ctx, body, user_id=user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify(config.model_dump()), 200

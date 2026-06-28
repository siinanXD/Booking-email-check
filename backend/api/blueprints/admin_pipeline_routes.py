"""Admin-Datenfluss-Routen: Funnel/Entscheidungen, Status, Stuck, Trace."""

from __future__ import annotations

from typing import Any

from flask import g, jsonify, request

from backend.api.blueprints.admin import _parse_days, admin_bp
from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.services.admin_pipeline_queries import admin_pipeline
from backend.api.services.admin_status_queries import admin_status
from backend.api.services.admin_stuck_queries import admin_stuck_mails
from backend.api.services.admin_trace_queries import admin_mail_trace


def _parse_hours(default: int = 24) -> int:
    raw = request.args.get("hours", str(default))
    try:
        hours = int(raw)
    except ValueError:
        hours = default
    return max(1, min(hours, 720))


@admin_bp.get("/pipeline")
@require_auth
@require_platform_admin
def admin_pipeline_route() -> tuple[Any, int]:
    """Pipeline-Funnel + Entscheidungs-Aggregation (plattformweit)."""
    data = admin_pipeline(g.ctx, days=_parse_days(30))
    return jsonify(data.model_dump()), 200


@admin_bp.get("/status")
@require_auth
@require_platform_admin
def admin_status_route() -> tuple[Any, int]:
    """System-Status-Ampel."""
    data = admin_status(g.ctx, g.settings)
    return jsonify(data.model_dump()), 200


@admin_bp.get("/mails/stuck")
@require_auth
@require_platform_admin
def admin_stuck_route() -> tuple[Any, int]:
    """Hängende (processing) oder verworfene (discarded) Mails."""
    kind = (request.args.get("kind") or "processing").strip().lower()
    data = admin_stuck_mails(g.ctx, hours=_parse_hours(24), kind=kind)
    return jsonify(data.model_dump()), 200


@admin_bp.get("/accounts/<account_id>/mails/<correlation_id>/trace")
@require_auth
@require_platform_admin
def admin_trace_route(account_id: str, correlation_id: str) -> tuple[Any, int]:
    """Einzel-Mail-Trace (cross-tenant, angereichert)."""
    result = admin_mail_trace(g.ctx, account_id, correlation_id)
    if result is None:
        return jsonify({"error": "Not found", "code": 404}), 404
    return jsonify(result.model_dump()), 200

"""Dashboard-Stats-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.services import dashboard_queries
from backend.api.services.api_helpers import tenant_query_service

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/stats")
@require_auth
@require_account
def stats() -> tuple[Any, int]:
    """KPI-Übersicht für das Dashboard."""
    svc = tenant_query_service()
    data = svc.dashboard_stats()
    if (
        g.settings.web_demo_data
        and g.settings.app_env == "development"
        and data.total_emails_week == 0
    ):
        data = svc.demo_stats()
    return jsonify(data.model_dump()), 200


@dashboard_bp.get("/mail-volume")
@require_auth
@require_account
def mail_volume() -> tuple[Any, int]:
    """Mail-/Kosten-Tagesreihe des eigenen Accounts (Dashboard-Trend)."""
    result = dashboard_queries.costs(
        g.ctx,
        get_request_account_id(),
        from_date=request.args.get("from_date"),
        to_date=request.args.get("to_date"),
        group_by=request.args.get("group_by", "day"),
    )
    return jsonify(result.model_dump()), 200

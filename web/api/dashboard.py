"""Dashboard-Stats-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify

from web.middleware.auth_guard import require_auth
from web.services.query_service import QueryService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/stats")
@require_auth
def stats() -> tuple[Any, int]:
    """KPI-Übersicht für das Dashboard."""
    svc = QueryService(g.ctx)
    data = svc.dashboard_stats()
    if (
        g.settings.web_demo_data
        and g.settings.app_env == "development"
        and data.total_emails_week == 0
    ):
        data = svc.demo_stats()
    return jsonify(data.model_dump()), 200

"""Plattform-Admin: Live-Aktivität (Mail-Verarbeitung + WhatsApp-Versand)."""

from __future__ import annotations

from typing import Any

from flask import g, jsonify, request

from backend.api.blueprints.admin import admin_bp
from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.services.admin_activity_queries import admin_activity


@admin_bp.get("/activity")
@require_auth
@require_platform_admin
def activity() -> tuple[Any, int]:
    """Operativer Überblick: zuletzt verarbeitete Mails und WhatsApp-Sends."""
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))
    data = admin_activity(g.ctx, notif_limit=limit, mail_limit=limit)
    return jsonify(data.model_dump(mode="json")), 200

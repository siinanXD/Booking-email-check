"""Plattform-Admin: Putzplan eines Mandanten (Diagnose, read-only)."""

from __future__ import annotations

from typing import Any

from flask import g, jsonify

from backend.api.blueprints.admin import admin_bp
from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.services.cleaning_queries import (
    feature_enabled,
    list_partners,
    list_tasks,
)


@admin_bp.get("/accounts/<account_id>/cleaning")
@require_auth
@require_platform_admin
def admin_account_cleaning(account_id: str) -> tuple[Any, int]:
    """Putzplan eines Mandanten zur Diagnose (Partner + Aufträge)."""
    if g.ctx.account_repo.get_by_id(account_id) is None:
        return jsonify({"error": "Account not found", "code": 404}), 404
    if not feature_enabled(g.ctx, account_id):
        return jsonify({"enabled": False, "partners": [], "tasks": []}), 200
    partners = list_partners(g.ctx, account_id)
    tasks = list_tasks(g.ctx, account_id)
    return (
        jsonify(
            {
                "enabled": True,
                "partners": [p.model_dump() for p in partners.items],
                "tasks": [t.model_dump() for t in tasks.items],
            }
        ),
        200,
    )

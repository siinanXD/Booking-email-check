"""Benachrichtigungs-Feed (Glocke) + „Alle als gelesen“."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.services.notification_feed import build_feed, mark_all_read

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _user_id() -> str:
    current = getattr(g, "current_user", None)
    uid = current.get("id") if isinstance(current, dict) else None
    return str(uid) if uid else ""


@notifications_bp.get("")
@require_auth
@require_account
def list_notifications() -> tuple[Any, int]:
    """Liefert das abgeleitete Feed inkl. Anzahl ungelesener Einträge."""
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    return jsonify(build_feed(g.ctx, account_id, _user_id()).model_dump()), 200


@notifications_bp.post("/read-all")
@require_auth
@require_account
def read_all() -> tuple[Any, int]:
    """Markiert alle aktuellen Benachrichtigungen als gelesen (je Benutzer)."""
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    mark_all_read(g.ctx.db, _user_id())
    return jsonify({"status": "ok"}), 200

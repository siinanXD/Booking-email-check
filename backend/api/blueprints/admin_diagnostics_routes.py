"""Plattform-Admin: Mail- und WhatsApp-Diagnose pro Mandant."""

from __future__ import annotations

from typing import Any

from flask import g, jsonify, request

from backend.api.blueprints.admin import admin_bp
from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import require_platform_admin
from backend.api.schemas.admin_diagnostics import (
    AdminWhatsAppTemplatesUpdate,
    AdminWhatsAppTestRequest,
)
from backend.api.services.admin_diagnostics_service import (
    AccountNotFoundError,
    AdminDiagnosticsService,
    RateLimitExceededError,
)


def _diagnostics() -> AdminDiagnosticsService:
    return AdminDiagnosticsService(g.ctx, g.settings)


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


@admin_bp.put("/accounts/<account_id>/whatsapp/templates")
@require_auth
@require_platform_admin
def admin_update_whatsapp_templates(account_id: str) -> tuple[Any, int]:
    """Speichert Meta-Template-Namen für Mandant-Diagnose."""
    body = AdminWhatsAppTemplatesUpdate.model_validate(
        request.get_json(silent=True) or {}
    )
    try:
        info = _diagnostics().update_whatsapp_templates(account_id, body)
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

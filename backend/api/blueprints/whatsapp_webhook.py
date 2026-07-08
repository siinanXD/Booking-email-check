"""WhatsApp Webhook – empfängt eingehende Nachrichten von Meta."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.rate_limit import limiter
from backend.features.notifications.whatsapp_echo_service import WhatsAppEchoService
from backend.features.notifications.whatsapp_incoming_service import (
    WhatsAppIncomingService,
)
from backend.features.whatsapp_bot.wiring import build_bot_service

logger = logging.getLogger(__name__)

whatsapp_webhook_bp = Blueprint(
    "whatsapp_webhook", __name__, url_prefix="/api/whatsapp"
)


@whatsapp_webhook_bp.get("/webhook")
def verify_webhook() -> tuple[Any, int]:
    """Meta-Webhook-Verifikation (einmalig beim Einrichten in Meta Developer Portal)."""
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    expected = g.settings.whatsapp_webhook_verify_token
    if not expected:
        logger.error("WHATSAPP_WEBHOOK_VERIFY_TOKEN nicht konfiguriert")
        return jsonify({"error": "not configured"}), 500

    if mode == "subscribe" and token == expected:
        logger.info("WhatsApp Webhook erfolgreich verifiziert")
        return challenge, 200

    logger.warning("WhatsApp Webhook Verifikation fehlgeschlagen – falscher Token")
    return jsonify({"error": "Forbidden"}), 403


@whatsapp_webhook_bp.post("/webhook")
@limiter.exempt
def receive_webhook() -> tuple[Any, int]:
    """Empfängt eingehende WhatsApp-Nachrichten und leitet sie an den Host weiter."""
    if not _verify_signature(request):
        logger.warning("WhatsApp Webhook: ungültige Signatur abgelehnt")
        return jsonify({"error": "Invalid signature"}), 403

    payload = request.get_json(silent=True) or {}

    if payload.get("object") != "whatsapp_business_account":
        return jsonify({"status": "ignored"}), 200

    if g.settings.whatsapp_echo_mode:
        echoed = WhatsAppEchoService(g.settings).handle(payload)
        return jsonify({"status": "echoed" if echoed else "skipped"}), 200

    account_id = _resolve_account_id(payload)
    if not account_id:
        logger.debug("Kein Account für eingehende WhatsApp-Nachricht gefunden")
        return jsonify({"status": "no_account"}), 200

    if g.settings.whatsapp_bot_enabled:
        bot = build_bot_service(g.ctx, g.settings, account_id=account_id)
        status = bot.handle(payload, account_id)
        return jsonify({"status": status}), 200

    svc = WhatsAppIncomingService(
        settings=g.settings,
        user_repo=g.ctx.user_repo,
        platform_settings_repo=g.ctx.platform_settings_repo,
    )
    forwarded = svc.handle(payload, account_id)
    return jsonify({"status": "forwarded" if forwarded else "skipped"}), 200


def _verify_signature(req: Any) -> bool:
    """Prüft X-Hub-Signature-256 von Meta (wenn WHATSAPP_APP_SECRET gesetzt)."""
    secret = g.settings.whatsapp_app_secret
    if not secret:
        if g.settings.app_env == "development" or g.settings.flask_env == "development":
            return True  # nur in Dev ohne App-Secret erlaubt
        logger.error(
            "WHATSAPP_APP_SECRET nicht konfiguriert – Webhook-Payload abgelehnt"
        )
        return False

    signature = req.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False

    mac = hmac.new(secret.encode(), req.get_data(), hashlib.sha256)
    return hmac.compare_digest(signature[7:], mac.hexdigest())


def _resolve_account_id(payload: dict[str, Any]) -> str | None:
    """Ermittelt Account-ID anhand der phone_number_id im Meta-Payload."""
    try:
        entry = payload.get("entry", [])
        if not entry:
            return None
        changes = entry[0].get("changes", [])
        if not changes:
            return None
        phone_number_id = (
            changes[0].get("value", {}).get("metadata", {}).get("phone_number_id", "")
        )
        if not phone_number_id:
            return None
        raw = g.ctx.platform_settings_repo.find_account_by_phone_number_id(
            phone_number_id
        )
        return str(raw) if raw else None
    except Exception:
        logger.exception("Fehler beim Auflösen der Account-ID aus Webhook-Payload")
        return None

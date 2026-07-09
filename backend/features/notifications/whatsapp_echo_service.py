"""Echo-Bot für den isolierten Test des Meta-Webhook-Kreislaufs (Schritt 1).

Nur aktiv wenn WHATSAPP_ECHO_MODE=true. Eingehende Text-Nachrichten werden
unverändert an den Absender zurückgeschickt – ohne Account-Zuordnung, ohne
LLM, ohne DB-Zugriff. Nachrichteninhalt bleibt Daten (keine Interpretation).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

from backend.core.config.settings import Settings
from backend.features.notifications.whatsapp_incoming_service import _extract_message

logger = logging.getLogger(__name__)

_ECHO_MAX_CHARS = 1000


class TextSender(Protocol):
    """Interface für einfache Text-Nachrichten an eine wa_id."""

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        """Sendet eine Text-Nachricht; True bei Erfolg."""
        ...


class MetaTextSender:
    """Text-Versand über die Meta Cloud API (Credentials aus .env)."""

    def __init__(self, settings: Settings) -> None:
        """Initialize with settings."""
        self._settings = settings

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        """Execute the operation."""
        token = self._settings.whatsapp_access_token.strip()
        phone_id = self._settings.whatsapp_phone_number_id.strip()
        if not token or not phone_id:
            logger.warning(
                "Echo-Modus: WHATSAPP_ACCESS_TOKEN oder "
                "WHATSAPP_PHONE_NUMBER_ID fehlt"
            )
            return False
        url = (
            f"https://graph.facebook.com/{self._settings.whatsapp_api_version}"
            f"/{phone_id}/messages"
        )
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": recipient_wa_id,
            "type": "text",
            "text": {"body": text},
        }
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            return True
        except Exception:
            logger.exception("Echo-Versand an %s fehlgeschlagen", recipient_wa_id)
            return False


class WhatsAppEchoService:
    """Beantwortet eingehende Text-Nachrichten mit einem Echo."""

    def __init__(self, settings: Settings, sender: TextSender | None = None) -> None:
        """Initialize with settings and optional sender (Tests: Mock)."""
        self._sender: TextSender = sender or MetaTextSender(settings)

    def handle(self, payload: dict[str, Any]) -> bool:
        """Verarbeitet einen Meta-Webhook-Payload im Echo-Modus.

        Gibt True zurück, wenn ein Echo gesendet wurde.
        """
        extracted = _extract_message(payload)
        if not extracted:
            return False
        sender_phone, sender_name, text = extracted
        echo_text = f"\U0001f501 *Echo an {sender_name}:*\n\n{text[:_ECHO_MAX_CHARS]}"
        sent = self._sender.send_text(sender_phone, echo_text)
        if sent:
            logger.info("Echo an %s gesendet (%d Zeichen)", sender_phone, len(text))
        return sent

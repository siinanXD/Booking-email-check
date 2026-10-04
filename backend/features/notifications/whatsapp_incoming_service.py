"""Eingehende WhatsApp-Nachrichten verarbeiten und an Host weiterleiten."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.core.config.settings import Settings
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def _extract_message(payload: dict[str, Any]) -> tuple[str, str, str] | None:
    """Gibt (sender_phone, sender_name, message_text) aus Meta-Payload zurück."""
    try:
        entry = payload.get("entry", [])
        if not entry:
            return None
        changes = entry[0].get("changes", [])
        if not changes:
            return None
        value = changes[0].get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None
        msg = messages[0]
        if msg.get("type") != "text":
            return None  # Bilder/Audio etc. ignorieren

        sender_phone = str(msg.get("from", "")).strip()
        text = msg.get("text", {}).get("body", "").strip()
        if not sender_phone or not text:
            return None

        contacts = value.get("contacts", [])
        sender_name = (
            contacts[0].get("profile", {}).get("name", sender_phone)
            if contacts
            else sender_phone
        )
        return sender_phone, str(sender_name), text
    except Exception:
        logger.exception("Fehler beim Parsen des WhatsApp-Payloads")
        return None


def _find_host_phone(account_id: str, user_repo: UserRepository) -> str | None:
    """Gibt die WhatsApp-Nummer des ersten aktiven Host-Users zurück."""
    try:
        for user in user_repo.list_by_account_id(account_id):
            if user.whatsapp_phone_e164 and user.whatsapp_enabled:
                return user.whatsapp_phone_e164
    except Exception:
        logger.exception("Fehler beim Suchen der Host-Nummer für %s", account_id)
    return None


class WhatsAppIncomingService:
    """Leitet eingehende WhatsApp-Antworten an den Host weiter."""

    def __init__(
        self,
        settings: Settings,
        user_repo: UserRepository,
        platform_settings_repo: PlatformSettingsRepository,
    ) -> None:
        """Initialize with dependencies."""
        self._settings = settings
        self._user_repo = user_repo
        self._platform_settings_repo = platform_settings_repo

    def handle(self, payload: dict[str, Any], account_id: str) -> bool:
        """Verarbeitet eingehenden Meta-Webhook-Payload.

        Gibt True zurück wenn eine Weiterleitung an den Host gesendet wurde.
        """
        extracted = _extract_message(payload)
        if not extracted:
            return False

        sender_phone, sender_name, text = extracted

        host_phone = _find_host_phone(account_id, self._user_repo)
        if not host_phone:
            logger.warning("Kein Host mit WhatsApp-Nummer für Account %s", account_id)
            return False

        # Effektive Einstellungen (DB überschreibt .env)
        db_settings = self._platform_settings_repo.get(account_id)
        token = (
            (db_settings.whatsapp_access_token if db_settings else None)
            or self._settings.whatsapp_access_token
        ).strip()
        phone_id = (
            (db_settings.whatsapp_phone_number_id if db_settings else None)
            or self._settings.whatsapp_phone_number_id
        ).strip()

        if not token or not phone_id:
            logger.warning("WhatsApp-Zugangsdaten für Account %s fehlen", account_id)
            return False

        forward_text = (
            f"\U0001f4e9 *Neue WhatsApp-Antwort*\n\n"
            f"Von: {sender_name} (+{sender_phone})\n\n"
            f"{text}"
        )
        url = (
            f"https://graph.facebook.com/{self._settings.whatsapp_api_version}"
            f"/{phone_id}/messages"
        )
        recipient = "".join(ch for ch in host_phone if ch.isdigit())
        msg_payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": forward_text},
        }
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=msg_payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            logger.info("WhatsApp-Antwort für Account %s weitergeleitet", account_id)
            return True
        except Exception:
            logger.exception(
                "Weiterleitung an Host fehlgeschlagen (Account %s)", account_id
            )
            return False

"""Ausgehender Versand des Bots über die Meta Cloud API (mockbar)."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

from backend.features.whatsapp_bot.models import BotButton, BotDocument, BotReply

logger = logging.getLogger(__name__)

_MAX_BUTTONS = 3
_MAX_BUTTON_TITLE = 20


class BotMessenger(Protocol):
    """Interface für alle ausgehenden Bot-Nachrichten."""

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        """Sendet eine Textnachricht."""
        ...

    def send_buttons(
        self, recipient_wa_id: str, text: str, buttons: list[BotButton]
    ) -> bool:
        """Sendet eine Interactive-Button-Nachricht (max. 3 Buttons)."""
        ...

    def send_document(self, recipient_wa_id: str, document: BotDocument) -> bool:
        """Lädt ein Dokument hoch und sendet es."""
        ...


def deliver_reply(
    messenger: BotMessenger, recipient_wa_id: str, reply: BotReply
) -> bool:
    """Versendet eine BotReply (Text/Buttons zuerst, dann Dokument)."""
    if reply.buttons:
        ok = messenger.send_buttons(recipient_wa_id, reply.text, reply.buttons)
    else:
        ok = messenger.send_text(recipient_wa_id, reply.text)
    if reply.document is not None:
        ok = messenger.send_document(recipient_wa_id, reply.document) and ok
    return ok


class MetaBotMessenger:
    """Meta Cloud API Implementierung."""

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v21.0",
    ) -> None:
        """Initialize with Meta credentials (aus effektiven Settings)."""
        self._token = access_token.strip()
        self._phone_id = phone_number_id.strip()
        self._api_version = api_version

    def _messages_url(self) -> str:
        return (
            f"https://graph.facebook.com/{self._api_version}"
            f"/{self._phone_id}/messages"
        )

    def _post_message(self, payload: dict[str, Any]) -> bool:
        if not self._token or not self._phone_id:
            logger.warning("WhatsApp-Bot: Zugangsdaten fehlen — Versand übersprungen")
            return False
        try:
            resp = httpx.post(
                self._messages_url(),
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            return True
        except Exception:
            logger.exception("WhatsApp-Bot: Versand fehlgeschlagen")
            return False

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        """Sendet eine Textnachricht."""
        return self._post_message(
            {
                "messaging_product": "whatsapp",
                "to": recipient_wa_id,
                "type": "text",
                "text": {"body": text},
            }
        )

    def send_buttons(
        self, recipient_wa_id: str, text: str, buttons: list[BotButton]
    ) -> bool:
        """Sendet Interactive Buttons (Meta-Limits werden hart durchgesetzt)."""
        trimmed = [
            {
                "type": "reply",
                "reply": {"id": b.id, "title": b.title[:_MAX_BUTTON_TITLE]},
            }
            for b in buttons[:_MAX_BUTTONS]
        ]
        return self._post_message(
            {
                "messaging_product": "whatsapp",
                "to": recipient_wa_id,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {"buttons": trimmed},
                },
            }
        )

    def send_document(self, recipient_wa_id: str, document: BotDocument) -> bool:
        """Media-Upload (multipart) → media_id → Dokument-Nachricht."""
        media_id = self._upload_media(document)
        if not media_id:
            return False
        return self._post_message(
            {
                "messaging_product": "whatsapp",
                "to": recipient_wa_id,
                "type": "document",
                "document": {"id": media_id, "filename": document.filename},
            }
        )

    def _upload_media(self, document: BotDocument) -> str | None:
        url = (
            f"https://graph.facebook.com/{self._api_version}" f"/{self._phone_id}/media"
        )
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
                data={"messaging_product": "whatsapp", "type": document.mime_type},
                files={
                    "file": (document.filename, document.content, document.mime_type)
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            media_id = resp.json().get("id")
            return str(media_id) if media_id else None
        except Exception:
            logger.exception("WhatsApp-Bot: Media-Upload fehlgeschlagen")
            return None

    def download_media(self, media_id: str) -> bytes | None:
        """Lädt eine eingehende Mediendatei (z. B. Sprachnachricht) herunter."""
        try:
            meta_url = f"https://graph.facebook.com/{self._api_version}/{media_id}"
            headers = {"Authorization": f"Bearer {self._token}"}
            info = httpx.get(meta_url, headers=headers, timeout=15.0)
            info.raise_for_status()
            file_url = info.json().get("url")
            if not file_url:
                return None
            blob = httpx.get(file_url, headers=headers, timeout=30.0)
            blob.raise_for_status()
            return blob.content
        except Exception:
            logger.exception("WhatsApp-Bot: Media-Download fehlgeschlagen")
            return None

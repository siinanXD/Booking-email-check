"""WhatsApp-Template-Versand über Meta Cloud API."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

from backend.core.config.settings import Settings
from backend.core.models.notification import WhatsAppSendResult, WhatsAppTemplateMessage

logger = logging.getLogger(__name__)


class WhatsAppClient(Protocol):
    """Interface für Template-Nachrichten."""

    def send_template(self, message: WhatsAppTemplateMessage) -> WhatsAppSendResult:
        """Sendet eine genehmigte WhatsApp-Template-Nachricht."""
        ...


class DisabledWhatsAppClient:
    """No-Op wenn WHATSAPP_ENABLED=false (Default)."""

    def send_template(self, message: WhatsAppTemplateMessage) -> WhatsAppSendResult:
        """Execute the operation."""
        _ = message
        return WhatsAppSendResult(
            success=True,
            dry_run=True,
            provider_message_id="disabled",
        )


def _validate_phone_number_id(phone_id: str) -> str | None:
    """Phone Number ID muss numerisch sein (Meta API), keine Rufnummer."""
    cleaned = phone_id.strip()
    if not cleaned:
        return "WHATSAPP_PHONE_NUMBER_ID fehlt"
    if any(ch in cleaned for ch in "+-() "):
        return (
            "WHATSAPP_PHONE_NUMBER_ID sieht wie eine Telefonnummer aus "
            f"({cleaned!r}). Trage die numerische ID aus Meta ein "
            "(WhatsApp → API Setup → Phone number ID), z. B. 123456789012345."
        )
    if not cleaned.isdigit():
        return (
            "WHATSAPP_PHONE_NUMBER_ID muss nur Ziffern enthalten "
            f"(aktuell: {cleaned!r})."
        )
    return None


class MetaCloudWhatsAppClient:
    """Meta WhatsApp Cloud API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the instance with its dependencies."""
        self._settings = settings

    def send_template(self, message: WhatsAppTemplateMessage) -> WhatsAppSendResult:
        """Execute the operation."""
        token = self._settings.whatsapp_access_token.strip()
        phone_id = self._settings.whatsapp_phone_number_id.strip()
        if not token or not phone_id:
            return WhatsAppSendResult(
                success=False,
                error="WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID missing",
            )
        phone_id_error = _validate_phone_number_id(phone_id)
        if phone_id_error:
            return WhatsAppSendResult(success=False, error=phone_id_error)
        url = (
            f"https://graph.facebook.com/{self._settings.whatsapp_api_version}"
            f"/{phone_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": _normalize_e164_digits(message.recipient_e164),
            "type": "template",
            "template": {
                "name": message.template_name,
                "language": {"code": message.template_language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": param}
                            for param in message.template_params
                        ],
                    }
                ],
            },
        }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            msg_id = _extract_message_id(data)
            return WhatsAppSendResult(success=True, provider_message_id=msg_id)
        except httpx.HTTPStatusError as exc:
            logger.exception("Meta WhatsApp send failed")
            return WhatsAppSendResult(success=False, error=_meta_api_error(exc))
        except Exception as exc:
            logger.exception("Meta WhatsApp send failed")
            return WhatsAppSendResult(success=False, error=str(exc))

    def send_hello_world(self, recipient_e164: str) -> WhatsAppSendResult:
        """Meta-Standardtestvorlage hello_world (en_US, ohne Parameter)."""
        token = self._settings.whatsapp_access_token.strip()
        phone_id = self._settings.whatsapp_phone_number_id.strip()
        if not token or not phone_id:
            return WhatsAppSendResult(
                success=False,
                error="WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID missing",
            )
        phone_id_error = _validate_phone_number_id(phone_id)
        if phone_id_error:
            return WhatsAppSendResult(success=False, error=phone_id_error)
        url = (
            f"https://graph.facebook.com/{self._settings.whatsapp_api_version}"
            f"/{phone_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": _normalize_e164_digits(recipient_e164),
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"},
            },
        }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            msg_id = _extract_message_id(data)
            return WhatsAppSendResult(success=True, provider_message_id=msg_id)
        except httpx.HTTPStatusError as exc:
            logger.exception("Meta WhatsApp hello_world test failed")
            return WhatsAppSendResult(
                success=False,
                error=_meta_api_error(exc),
            )
        except Exception as exc:
            logger.exception("Meta WhatsApp hello_world test failed")
            return WhatsAppSendResult(success=False, error=str(exc))


def send_whatsapp_hello_world_test(
    settings: Settings,
    recipient_e164: str,
) -> WhatsAppSendResult:
    """Verbindungstest via hello_world – unabhängig von WHATSAPP_ENABLED."""
    return MetaCloudWhatsAppClient(settings).send_hello_world(recipient_e164)


_ADMIN_TEST_PARAMS: dict[str, list[str]] = {
    "cleaning_task": [
        "Test-Unterkunft",
        "01.06.2026",
        "05.06.2026",
        "Standard",
        "TEST-001",
    ],
    "status_notice": [
        "Neue Buchung",
        "Test-Unterkunft",
        "01.06.2026",
        "05.06.2026",
        "Max Mustermann",
        "TEST-001",
    ],
    "guest_inquiry": [
        "Gastanfrage",
        "Test-Unterkunft",
        "TEST-001",
        "01.06.2026",
        "05.06.2026",
        "Max Mustermann",
    ],
    "support_ticket": [
        "Test-Mandant",
        "Hoch",
        "admin@test.local",
        "Kurze Testnachricht für Support-Ticket.",
    ],
}


def send_whatsapp_admin_test(
    settings: Settings,
    recipient_e164: str,
    template: str,
) -> WhatsAppSendResult:
    """Admin-Diagnose: hello_world oder konfigurierte Mandanten-Templates."""
    if template == "hello_world":
        return send_whatsapp_hello_world_test(settings, recipient_e164)
    name_map = {
        "cleaning_task": settings.whatsapp_template_cleaning_task,
        "status_notice": settings.whatsapp_template_status_notice,
        "guest_inquiry": settings.whatsapp_template_guest_inquiry,
        "support_ticket": settings.whatsapp_template_support_ticket,
    }
    template_name = name_map.get(template)
    if not template_name:
        return WhatsAppSendResult(
            success=False,
            error=f"Unbekanntes Test-Template: {template!r}",
        )
    params = _ADMIN_TEST_PARAMS.get(template, [])
    message = WhatsAppTemplateMessage(
        recipient_e164=recipient_e164,
        template_name=template_name,
        template_language=settings.whatsapp_template_language,
        template_params=params,
    )
    return MetaCloudWhatsAppClient(settings).send_template(message)


def build_whatsapp_client(settings: Settings) -> WhatsAppClient:
    """Factory: disabled default, sonst Meta Cloud API."""
    if not settings.whatsapp_enabled:
        return DisabledWhatsAppClient()
    return MetaCloudWhatsAppClient(settings)


def _meta_api_error(exc: httpx.HTTPStatusError) -> str:
    """Lesbare Meta-Graph-Fehlermeldung (z. B. abgelaufener Token)."""
    try:
        body = exc.response.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            message = err.get("message") or err.get("error_user_msg")
            code = err.get("code")
            if message and code:
                return f"Meta API ({exc.response.status_code}, code {code}): {message}"
            if message:
                return f"Meta API ({exc.response.status_code}): {message}"
    except Exception:
        pass
    return str(exc)


def _normalize_e164_digits(phone: str) -> str:
    digits = "".join(ch for ch in phone.strip() if ch.isdigit())
    if phone.strip().startswith("+"):
        return digits
    return digits


def _extract_message_id(data: dict[str, Any]) -> str | None:
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            mid = first.get("id")
            return str(mid) if mid else None
    return None

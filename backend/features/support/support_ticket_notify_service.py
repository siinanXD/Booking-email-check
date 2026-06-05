"""WhatsApp-Benachrichtigung bei neuem Support-Ticket."""

from __future__ import annotations

import logging
import re

from backend.core.config.settings import Settings
from backend.core.models.notification import WhatsAppTemplateMessage
from backend.core.models.support_ticket import URGENCY_LABELS, SupportTicketRecord
from backend.features.notifications.whatsapp_client import (
    WhatsAppClient,
    build_whatsapp_client,
)
from backend.infrastructure.repositories.platform_admin_config_repository import (
    PlatformAdminConfigRepository,
)

logger = logging.getLogger(__name__)

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def _message_excerpt(text: str, max_len: int = 200) -> str:
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 1] + "…"


def effective_support_admin_settings(
    settings: Settings,
    config_repo: PlatformAdminConfigRepository,
) -> tuple[str, str]:
    """Admin-Nummer und Template-Name (Mongo mit .env-Fallback)."""
    stored = config_repo.get_or_default()
    phone = (stored.platform_admin_whatsapp_e164 or "").strip()
    if not phone:
        phone = settings.platform_admin_whatsapp_e164.strip()
    template = (stored.whatsapp_template_support_ticket or "").strip()
    if not template:
        template = settings.whatsapp_template_support_ticket
    return phone, template


class SupportTicketNotifyService:
    """Versendet Admin-Alert per WhatsApp-Template."""

    def __init__(
        self,
        settings: Settings,
        config_repo: PlatformAdminConfigRepository,
        whatsapp_client: WhatsAppClient | None = None,
    ) -> None:
        self._settings = settings
        self._config_repo = config_repo
        self._whatsapp_client = whatsapp_client

    def _client(self) -> WhatsAppClient:
        if self._whatsapp_client is not None:
            return self._whatsapp_client
        return build_whatsapp_client(self._settings)

    def notify_new_ticket(
        self,
        ticket: SupportTicketRecord,
        *,
        account_display_name: str,
    ) -> tuple[str, str | None, str | None]:
        """Returns (whatsapp_notify_status, error, message_id)."""
        if not self._settings.whatsapp_enabled:
            return "skipped", None, None

        recipient, template_name = effective_support_admin_settings(
            self._settings,
            self._config_repo,
        )
        if not recipient or not _E164_RE.match(recipient):
            return "skipped", "PLATFORM_ADMIN_WHATSAPP_E164 not configured", None

        tenant_label = account_display_name.strip() or ticket.account_id[:8]
        urgency_label = URGENCY_LABELS.get(ticket.urgency, ticket.urgency)
        excerpt = _message_excerpt(ticket.message)

        message = WhatsAppTemplateMessage(
            recipient_e164=recipient,
            template_name=template_name,
            template_language=self._settings.whatsapp_template_language,
            template_params=[
                tenant_label,
                urgency_label,
                ticket.created_by_email,
                excerpt,
            ],
        )
        result = self._client().send_template(message)
        if result.success:
            logger.info(
                "Support ticket WhatsApp sent ticket_id=%s account_id=%s",
                ticket.ticket_id,
                ticket.account_id,
            )
            return "sent", None, result.provider_message_id
        error = (result.error or "WhatsApp send failed")[:500]
        logger.warning(
            "Support ticket WhatsApp failed ticket_id=%s error=%s",
            ticket.ticket_id,
            error,
        )
        return "failed", error, None

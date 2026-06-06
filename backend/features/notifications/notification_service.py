"""Fachliche WhatsApp-Events nach Human-Review-Freigabe."""

from __future__ import annotations

import logging

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.settings import Settings
from backend.core.models.notification import (
    NotificationKind,
    NotificationOutboxRecord,
    NotificationStatus,
    WhatsAppTemplateMessage,
)
from backend.features.notifications.notification_template_payload import (
    build_template_payload,
    kind_for_extraction,
    kind_for_recipient,
    parse_recipient_list,
)
from backend.features.notifications.whatsapp_client import (
    WhatsAppClient,
    build_whatsapp_client,
)
from backend.features.notifications.whatsapp_locale import DEFAULT_EMPLOYEE_LOCALE
from backend.features.platform.effective_settings import merge_platform_settings
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository

_HOST_RECIPIENT_ROLE = "host"
_EMPLOYEE_RECIPIENT_ROLE = "employee"

logger = logging.getLogger(__name__)


class NotificationService:
    """Erzeugt Outbox-Einträge und versendet WhatsApp nach Freigabe."""

    def __init__(
        self,
        settings: Settings,
        notification_repo: NotificationRepository,
        user_repo: UserRepository,
        property_recipient_repo: PropertyRecipientRepository,
        platform_settings_repo: PlatformSettingsRepository,
        whatsapp_client: WhatsAppClient | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._settings = settings
        self._notification_repo = notification_repo
        self._user_repo = user_repo
        self._property_recipient_repo = property_recipient_repo
        self._platform_settings_repo = platform_settings_repo
        self._whatsapp_client = whatsapp_client

    def _effective_settings(self, account_id: str | None = None) -> Settings:
        if not account_id:
            return self._settings
        platform = self._platform_settings_repo.get(account_id)
        return merge_platform_settings(self._settings, platform)

    def _client(self, settings: Settings) -> WhatsAppClient:
        if self._whatsapp_client is not None:
            return self._whatsapp_client
        return build_whatsapp_client(settings)

    def dispatch_on_detect_if_enabled(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        *,
        account_id: str | None = None,
    ) -> list[NotificationOutboxRecord]:
        """Optional sofort nach Erkennung (WHATSAPP_AUTO_ON_DETECT), idempotent."""
        settings = self._effective_settings(account_id)
        if not settings.whatsapp_auto_on_detect:
            return []
        return self.dispatch_after_approval(
            correlation_id,
            extraction,
            account_id=account_id,
        )

    def dispatch_after_approval(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        *,
        account_id: str | None = None,
    ) -> list[NotificationOutboxRecord]:
        """Nach Review-Freigabe: Events erzeugen, idempotent senden."""
        settings = self._effective_settings(account_id)
        if not settings.whatsapp_enabled:
            logger.debug("WhatsApp disabled – skip notification for %s", correlation_id)
            return []

        if kind_for_extraction(extraction) is None:
            logger.info(
                "No WhatsApp template mapping for intent %s (%s)",
                extraction.intent,
                correlation_id,
            )
            return []

        recipients = self._resolve_recipients(
            extraction, settings, account_id=account_id
        )
        if not recipients:
            logger.warning(
                "No WhatsApp recipients configured for %s",
                correlation_id,
            )
            return []

        client = self._client(settings)
        results: list[NotificationOutboxRecord] = []
        host_locale = (
            settings.whatsapp_template_language.strip() or DEFAULT_EMPLOYEE_LOCALE
        )
        for recipient, recipient_locale, role in recipients:
            kind = kind_for_recipient(extraction, role)
            if kind is None:
                continue
            locale = recipient_locale
            if (
                kind != NotificationKind.BOOKING_CLEANING_TASK
                or role != _EMPLOYEE_RECIPIENT_ROLE
            ):
                locale = host_locale
            template_name, params, template_language = build_template_payload(
                kind,
                extraction,
                settings,
                locale=locale,
            )
            record = self._dispatch_one(
                correlation_id=correlation_id,
                kind=kind,
                recipient=recipient,
                template_name=template_name,
                template_params=params,
                template_language=template_language,
                settings=settings,
                client=client,
            )
            if record is not None:
                results.append(record)
        return results

    def _dispatch_one(
        self,
        *,
        correlation_id: str,
        kind: NotificationKind,
        recipient: str,
        template_name: str,
        template_params: list[str],
        template_language: str,
        settings: Settings,
        client: WhatsAppClient,
    ) -> NotificationOutboxRecord | None:
        idempotency_key = f"{correlation_id}:{kind.value}:{recipient}"
        pending = self._notification_repo.new_record(
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            kind=kind,
            recipient_e164=recipient,
            template_name=template_name,
            template_params=template_params,
            template_language=template_language,
        )
        claimed = self._notification_repo.try_claim(pending)
        if claimed is None:
            return None

        message = WhatsAppTemplateMessage(
            recipient_e164=recipient,
            template_name=template_name,
            template_language=template_language,
            template_params=template_params,
        )
        result = client.send_template(message)
        provider = "meta"

        if result.dry_run:
            self._notification_repo.mark_skipped(
                claimed.id, "whatsapp_disabled_dry_run"
            )
            claimed.status = NotificationStatus.SKIPPED
            return claimed

        if result.success:
            self._notification_repo.mark_sent(
                claimed.id,
                provider=provider,
                provider_message_id=result.provider_message_id,
            )
            claimed.status = NotificationStatus.SENT
            claimed.provider = provider
            claimed.provider_message_id = result.provider_message_id
            return claimed

        self._notification_repo.mark_failed(claimed.id, result.error or "send failed")
        claimed.status = NotificationStatus.FAILED
        claimed.error = result.error
        return claimed

    def _resolve_recipients(
        self,
        extraction: BookingExtraction,
        settings: Settings,
        *,
        account_id: str | None = None,
    ) -> list[tuple[str, str, str]]:
        """Host in Account-Sprache; Mitarbeiter-Sprache nur für Reinigungsaufträge."""
        host_locale = (
            settings.whatsapp_template_language.strip() or DEFAULT_EMPLOYEE_LOCALE
        )
        targets: dict[str, tuple[str, str]] = {}
        for phone in self._user_repo.list_whatsapp_recipient_phones(account_id):
            targets[phone] = (host_locale, _HOST_RECIPIENT_ROLE)
        for phone in parse_recipient_list(settings.whatsapp_default_recipients):
            targets[phone] = (host_locale, _HOST_RECIPIENT_ROLE)

        intent = extraction.intent
        if intent in (BookingIntent.NEW_BOOKING, None):
            for employee in self._property_recipient_repo.get_employees(
                extraction.property_name,
                account_id=account_id,
            ):
                targets[employee.phone_e164] = (
                    employee.locale,
                    _EMPLOYEE_RECIPIENT_ROLE,
                )

        return sorted(
            (phone, locale, role) for phone, (locale, role) in targets.items()
        )

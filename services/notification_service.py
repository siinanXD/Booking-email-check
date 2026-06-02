"""Fachliche WhatsApp-Events nach Human-Review-Freigabe."""

from __future__ import annotations

import logging
import re
from datetime import date

from config.settings import Settings
from models.notification import (
    NotificationKind,
    NotificationOutboxRecord,
    NotificationStatus,
    WhatsAppTemplateMessage,
)
from repositories.notification_repository import NotificationRepository
from repositories.platform_settings_repository import PlatformSettingsRepository
from repositories.property_recipient_repository import PropertyRecipientRepository
from repositories.user_repository import UserRepository
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from services.effective_settings import merge_platform_settings
from services.whatsapp_client import WhatsAppClient, build_whatsapp_client

logger = logging.getLogger(__name__)

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


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

    def _effective_settings(self) -> Settings:
        platform = self._platform_settings_repo.get()
        return merge_platform_settings(self._settings, platform)

    def _client(self, settings: Settings) -> WhatsAppClient:
        if self._whatsapp_client is not None:
            return self._whatsapp_client
        return build_whatsapp_client(settings)

    def dispatch_after_approval(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
    ) -> list[NotificationOutboxRecord]:
        """Nach Review-Freigabe: Events erzeugen, idempotent senden."""
        settings = self._effective_settings()
        if not settings.whatsapp_enabled:
            logger.debug("WhatsApp disabled – skip notification for %s", correlation_id)
            return []

        kind = _kind_for_extraction(extraction)
        if kind is None:
            logger.info(
                "No WhatsApp template mapping for intent %s (%s)",
                extraction.intent,
                correlation_id,
            )
            return []

        template_name, params = _build_template_payload(kind, extraction, settings)
        recipients = self._resolve_recipients(extraction, settings)
        if not recipients:
            logger.warning(
                "No WhatsApp recipients configured for %s",
                correlation_id,
            )
            return []

        client = self._client(settings)
        results: list[NotificationOutboxRecord] = []
        for recipient in recipients:
            record = self._dispatch_one(
                correlation_id=correlation_id,
                kind=kind,
                recipient=recipient,
                template_name=template_name,
                template_params=params,
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
            template_language=settings.whatsapp_template_language,
        )
        claimed = self._notification_repo.try_claim(pending)
        if claimed is None:
            return None

        message = WhatsAppTemplateMessage(
            recipient_e164=recipient,
            template_name=template_name,
            template_language=settings.whatsapp_template_language,
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
    ) -> list[str]:
        """Host immer; bei neuer Buchung zusaetzlich Putzfrau/Mitarbeiter."""
        phones: set[str] = set()
        for phone in self._user_repo.list_whatsapp_recipient_phones():
            phones.add(phone)
        for phone in _parse_recipient_list(settings.whatsapp_default_recipients):
            phones.add(phone)

        intent = extraction.intent
        if intent in (BookingIntent.NEW_BOOKING, None):
            property_phones = self._property_recipient_repo.get_phones(
                extraction.property_name
            )
            phones.update(property_phones)

        return sorted(phones)


def _kind_for_extraction(extraction: BookingExtraction) -> NotificationKind | None:
    intent = extraction.intent
    if intent in (BookingIntent.NEW_BOOKING, None):
        return NotificationKind.BOOKING_CLEANING_TASK
    if intent in (
        BookingIntent.CHANGE,
        BookingIntent.CANCELLATION,
        BookingIntent.PAYMENT_ISSUE,
    ):
        return NotificationKind.BOOKING_STATUS_NOTICE
    if intent in (BookingIntent.GUEST_INQUIRY, BookingIntent.COMPLAINT):
        return NotificationKind.BOOKING_GUEST_INQUIRY
    return None


def _build_template_payload(
    kind: NotificationKind,
    extraction: BookingExtraction,
    settings: Settings,
) -> tuple[str, list[str]]:
    if kind == NotificationKind.BOOKING_CLEANING_TASK:
        return settings.whatsapp_template_cleaning_task, [
            _text(extraction.property_name, "Unbekannte Unterkunft"),
            _format_date(extraction.check_in),
            _format_date(extraction.check_out),
            _cleaning_label(extraction),
            _text(extraction.booking_number, "—"),
        ]
    if kind == NotificationKind.BOOKING_GUEST_INQUIRY:
        return settings.whatsapp_template_guest_inquiry, [
            _inquiry_label(extraction),
            _text(extraction.property_name, "Unbekannte Unterkunft"),
            _text(extraction.booking_number, "—"),
            _format_date(extraction.check_in),
            _format_date(extraction.check_out),
            _text(extraction.guest_name, "—"),
        ]
    return settings.whatsapp_template_status_notice, [
        _status_label(extraction),
        _text(extraction.property_name, "Unbekannte Unterkunft"),
        _format_date(extraction.check_in),
        _format_date(extraction.check_out),
        _text(extraction.guest_name, "—"),
        _text(extraction.booking_number, "—"),
    ]


def _parse_recipient_list(raw: str) -> list[str]:
    if not raw.strip():
        return []
    result: list[str] = []
    for part in raw.split(","):
        phone = part.strip()
        if phone and _E164_RE.match(phone):
            result.append(phone)
    return result


def _text(value: str | None, fallback: str) -> str:
    if value and value.strip():
        return value.strip()
    return fallback


def _format_date(value: date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _cleaning_label(extraction: BookingExtraction) -> str:
    if extraction.intent == BookingIntent.NEW_BOOKING:
        return "Check-out Reinigung"
    return _text(extraction.status, "Reinigung")


def _status_label(extraction: BookingExtraction) -> str:
    if extraction.intent == BookingIntent.CANCELLATION:
        return "Storno"
    if extraction.intent == BookingIntent.CHANGE:
        return "Änderung"
    if extraction.intent == BookingIntent.PAYMENT_ISSUE:
        return "Zahlungsproblem"
    return _text(extraction.status, "Update")


def _inquiry_label(extraction: BookingExtraction) -> str:
    if extraction.intent == BookingIntent.COMPLAINT:
        return "Beschwerde"
    return "Gastnachricht"

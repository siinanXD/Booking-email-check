"""WhatsApp-Template-Auswahl und Parameter."""

from __future__ import annotations

import re
from datetime import date

from backend.ai.domain.booking.beds24_fields import expects_room
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.settings import Settings
from backend.core.models.notification import NotificationKind
from backend.features.notifications.whatsapp_locale import (
    DEFAULT_EMPLOYEE_LOCALE,
    cleaning_label,
    inquiry_label,
    normalize_employee_locale,
    status_label,
    template_name_for_kind,
    unknown_property_label,
)

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def kind_for_extraction(extraction: BookingExtraction) -> NotificationKind | None:
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


def kind_for_recipient(
    extraction: BookingExtraction,
    role: str,
) -> NotificationKind | None:
    """Template-Typ pro Empfänger: Host vs. Mitarbeiter bei neuer Buchung."""
    intent = extraction.intent
    if intent in (BookingIntent.NEW_BOOKING, None):
        if role == "employee":
            return NotificationKind.BOOKING_CLEANING_TASK
        if role == "host":
            return NotificationKind.BOOKING_STATUS_NOTICE
    return kind_for_extraction(extraction)


def build_template_payload(
    kind: NotificationKind,
    extraction: BookingExtraction,
    settings: Settings,
    *,
    locale: str | None = None,
) -> tuple[str, list[str], str]:
    """Returns (template_name, params, template_language)."""
    account_lang = (
        settings.whatsapp_template_language.strip() or DEFAULT_EMPLOYEE_LOCALE
    )
    # Putzpartner-Templates folgen der Empfänger-Sprache, sonst Account-Sprache.
    partner_kinds = (
        NotificationKind.BOOKING_CLEANING_TASK,
        NotificationKind.CLEANING_CANCELLED,
    )
    if kind in partner_kinds:
        lang = normalize_employee_locale(locale or account_lang)
    else:
        lang = normalize_employee_locale(account_lang)
    template_name = template_name_for_kind(kind, settings, lang)
    if kind == NotificationKind.BOOKING_CLEANING_TASK:
        return (
            template_name,
            [
                _property_display(extraction, lang),
                _format_date(extraction.check_in),
                _format_date(extraction.check_out),
                _cleaning_label(extraction, lang),
                _text(extraction.booking_number, "—"),
            ],
            lang,
        )
    if kind == NotificationKind.CLEANING_CANCELLED:
        return (
            template_name,
            [
                _property_display(extraction, lang),
                _format_date(extraction.check_in),
                _format_date(extraction.check_out),
                _text(extraction.guest_name, "—"),
                _text(extraction.booking_number, "—"),
            ],
            lang,
        )
    if kind == NotificationKind.BOOKING_GUEST_INQUIRY:
        return (
            template_name,
            [
                _inquiry_label(extraction, lang),
                _property_display(extraction, lang),
                _text(extraction.booking_number, "—"),
                _format_date(extraction.check_in),
                _format_date(extraction.check_out),
                _text(extraction.guest_name, "—"),
            ],
            lang,
        )
    return (
        template_name,
        [
            _status_label(extraction, lang),
            _text(extraction.property_name, unknown_property_label(lang)),
            _format_date(extraction.check_in),
            _format_date(extraction.check_out),
            _text(extraction.guest_name, "—"),
            _text(extraction.booking_number, "—"),
        ],
        lang,
    )


def parse_recipient_list(raw: str) -> list[str]:
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


def _property_display(extraction: BookingExtraction, locale: str) -> str:
    """Anzeige-Unterkunft: Objekt + Zimmer + Kanal (nur fürs Template).

    Reutilisiert den bestehenden Property-Parameter — keine Meta-Template-
    Änderung nötig. Bei Multi-Zimmer-Objekten steht IMMER ein Zimmer-Feld: mit
    Nummer wenn erkannt, sonst sichtbar „unbekannt" (statt still wegzulassen).
    Ganz-Apartments (z. B. RebenGlück) bleiben ohne Zimmer.
    """
    label = _text(extraction.property_name, unknown_property_label(locale))
    room = (extraction.room_number or "").strip()
    if room:
        label = f"{label} - Zimmer Nr. {room}"
    elif expects_room(extraction.property_name):
        label = f"{label} - Zimmer Nr.: unbekannt"
    channel = (extraction.channel or "").strip()
    if channel:
        label = f"{label} ({channel})"
    return label


def _format_date(value: date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _cleaning_label(extraction: BookingExtraction, locale: str) -> str:
    return cleaning_label(
        is_new_booking=extraction.intent == BookingIntent.NEW_BOOKING,
        status=extraction.status,
        locale=locale,
    )


def _status_label(extraction: BookingExtraction, locale: str) -> str:
    return status_label(
        is_new_booking=extraction.intent == BookingIntent.NEW_BOOKING,
        is_cancellation=extraction.intent == BookingIntent.CANCELLATION,
        is_change=extraction.intent == BookingIntent.CHANGE,
        is_payment_issue=extraction.intent == BookingIntent.PAYMENT_ISSUE,
        status=extraction.status,
        locale=locale,
    )


def _inquiry_label(extraction: BookingExtraction, locale: str) -> str:
    return inquiry_label(
        is_complaint=extraction.intent == BookingIntent.COMPLAINT,
        locale=locale,
    )

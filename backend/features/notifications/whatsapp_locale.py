"""WhatsApp-Sprachen für Mitarbeiter-Empfänger (Meta-Template-Auflösung)."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.core.models.notification import NotificationKind

EMPLOYEE_WHATSAPP_LOCALES: frozenset[str] = frozenset({"de", "en", "pl", "it", "es"})

DEFAULT_EMPLOYEE_LOCALE = "de"

_UNKNOWN_PROPERTY: dict[str, str] = {
    "de": "Unbekannte Unterkunft",
    "en": "Unknown property",
    "pl": "Nieznany obiekt",
    "it": "Struttura sconosciuta",
    "es": "Alojamiento desconocido",
}

_CLEANING_NEW: dict[str, str] = {
    "de": "Check-out Reinigung",
    "en": "Check-out cleaning",
    "pl": "Sprzątanie po wymeldowaniu",
    "it": "Pulizia post check-out",
    "es": "Limpieza tras check-out",
}

_CLEANING_DEFAULT: dict[str, str] = {
    "de": "Reinigung",
    "en": "Cleaning",
    "pl": "Sprzątanie",
    "it": "Pulizia",
    "es": "Limpieza",
}

_STATUS_CANCELLATION: dict[str, str] = {
    "de": "Storno",
    "en": "Cancellation",
    "pl": "Anulowanie",
    "it": "Cancellazione",
    "es": "Cancelación",
}

_STATUS_CHANGE: dict[str, str] = {
    "de": "Änderung",
    "en": "Change",
    "pl": "Zmiana",
    "it": "Modifica",
    "es": "Cambio",
}

_STATUS_PAYMENT: dict[str, str] = {
    "de": "Zahlungsproblem",
    "en": "Payment issue",
    "pl": "Problem z płatnością",
    "it": "Problema di pagamento",
    "es": "Problema de pago",
}

_STATUS_DEFAULT: dict[str, str] = {
    "de": "Update",
    "en": "Update",
    "pl": "Aktualizacja",
    "it": "Aggiornamento",
    "es": "Actualización",
}

_INQUIRY_COMPLAINT: dict[str, str] = {
    "de": "Beschwerde",
    "en": "Complaint",
    "pl": "Reklamacja",
    "it": "Reclamo",
    "es": "Queja",
}

_INQUIRY_DEFAULT: dict[str, str] = {
    "de": "Gastnachricht",
    "en": "Guest message",
    "pl": "Wiadomość gościa",
    "it": "Messaggio ospite",
    "es": "Mensaje del huésped",
}


def normalize_employee_locale(locale: str | None) -> str:
    """Gültige Mitarbeiter-Sprache oder Fallback Deutsch."""
    key = (locale or "").strip().lower()
    if key in EMPLOYEE_WHATSAPP_LOCALES:
        return key
    return DEFAULT_EMPLOYEE_LOCALE


def localized_template_name(base_name: str, locale: str) -> str:
    """Leitet Meta-Template-Namen aus dem deutschen Basis-Namen ab."""
    locale = normalize_employee_locale(locale)
    if locale == DEFAULT_EMPLOYEE_LOCALE:
        return base_name
    if base_name.endswith("_de"):
        return f"{base_name.removesuffix('_de')}_{locale}"
    return f"{base_name}_{locale}"


def template_name_for_kind(
    kind: NotificationKind,
    settings: Settings,
    locale: str,
) -> str:
    """Template-Name für Intent + Sprache (Mehrsprachig nur Reinigung/Mitarbeiter)."""
    if kind == NotificationKind.BOOKING_CLEANING_TASK:
        return localized_template_name(settings.whatsapp_template_cleaning_task, locale)
    if kind == NotificationKind.BOOKING_GUEST_INQUIRY:
        return settings.whatsapp_template_guest_inquiry
    return settings.whatsapp_template_status_notice


def unknown_property_label(locale: str) -> str:
    return _UNKNOWN_PROPERTY.get(
        normalize_employee_locale(locale), _UNKNOWN_PROPERTY["de"]
    )


def cleaning_label(*, is_new_booking: bool, status: str | None, locale: str) -> str:
    loc = normalize_employee_locale(locale)
    if is_new_booking:
        return _CLEANING_NEW[loc]
    if status and status.strip():
        return status.strip()
    return _CLEANING_DEFAULT[loc]


def status_label(
    *,
    is_cancellation: bool,
    is_change: bool,
    is_payment_issue: bool,
    status: str | None,
    locale: str,
) -> str:
    loc = normalize_employee_locale(locale)
    if is_cancellation:
        return _STATUS_CANCELLATION[loc]
    if is_change:
        return _STATUS_CHANGE[loc]
    if is_payment_issue:
        return _STATUS_PAYMENT[loc]
    if status and status.strip():
        return status.strip()
    return _STATUS_DEFAULT[loc]


def inquiry_label(*, is_complaint: bool, locale: str) -> str:
    loc = normalize_employee_locale(locale)
    if is_complaint:
        return _INQUIRY_COMPLAINT[loc]
    return _INQUIRY_DEFAULT[loc]

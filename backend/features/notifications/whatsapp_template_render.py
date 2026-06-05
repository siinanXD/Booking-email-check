"""Rendert lesbare WhatsApp-Nachrichten aus Template-Parametern (Review-Vorschau)."""

from __future__ import annotations

from backend.core.models.notification import NotificationKind
from backend.features.notifications.whatsapp_locale import (
    DEFAULT_EMPLOYEE_LOCALE,
    normalize_employee_locale,
)

_TEMPLATE_BODIES: dict[NotificationKind, dict[str, str]] = {
    NotificationKind.BOOKING_CLEANING_TASK: {
        "de": (
            "Neue Reinigungsaufgabe für dein Team.\n\n"
            "Unterkunft: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Art der Reinigung: {{4}}\n"
            "Buchungsnummer: {{5}}\n\n"
            "Bitte die Reinigung vor dem nächsten Gast abschließen. Vielen Dank!"
        ),
        "en": (
            "You have received a new cleaning assignment.\n\n"
            "Property: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Task type: {{4}}\n"
            "Booking reference: {{5}}\n\n"
            "Please complete the cleaning before the next guest arrives. Thank you!"
        ),
        "pl": (
            "Masz nowe zlecenie sprzątania.\n\n"
            "Obiekt: {{1}}\n"
            "Zameldowanie: {{2}}\n"
            "Wymeldowanie: {{3}}\n"
            "Rodzaj zadania: {{4}}\n"
            "Numer rezerwacji: {{5}}\n\n"
            "Prosimy o sprzątanie przed przyjazdem kolejnego gościa. Dziękujemy!"
        ),
        "it": (
            "Hai ricevuto un nuovo incarico di pulizia.\n\n"
            "Struttura: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Tipo di incarico: {{4}}\n"
            "Riferimento prenotazione: {{5}}\n\n"
            "Completa la pulizia prima dell'arrivo del prossimo ospite. Grazie!"
        ),
        "es": (
            "Has recibido una nueva tarea de limpieza.\n\n"
            "Alojamiento: {{1}}\n"
            "Entrada: {{2}}\n"
            "Salida: {{3}}\n"
            "Tipo de tarea: {{4}}\n"
            "Referencia de reserva: {{5}}\n\n"
            "Completa la limpieza antes de la llegada del próximo huésped. ¡Gracias!"
        ),
    },
    NotificationKind.BOOKING_STATUS_NOTICE: {
        "de": (
            "Buchungsupdate: {{1}}\n\n"
            "Unterkunft: {{2}}\n"
            "Check-in: {{3}}\n"
            "Check-out: {{4}}\n"
            "Gast: {{5}}\n"
            "Buchung: {{6}}"
        ),
    },
    NotificationKind.BOOKING_GUEST_INQUIRY: {
        "de": (
            "{{1}}\n\n"
            "Unterkunft: {{2}}\n"
            "Buchung: {{3}}\n"
            "Check-in: {{4}}\n"
            "Check-out: {{5}}\n"
            "Gast: {{6}}"
        ),
    },
}


def render_whatsapp_body(
    kind: NotificationKind,
    params: list[str],
    locale: str,
) -> str:
    """Lesbarer Nachrichtentext für Review (Meta-Template-Struktur)."""
    loc = normalize_employee_locale(locale)
    bodies = _TEMPLATE_BODIES.get(kind)
    if bodies is None:
        return "\n".join(params)
    shell = bodies.get(loc) or bodies[DEFAULT_EMPLOYEE_LOCALE]
    rendered = shell
    for index, param in enumerate(params, start=1):
        rendered = rendered.replace(f"{{{{{index}}}}}", param)
    return rendered

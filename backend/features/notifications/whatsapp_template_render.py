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
    NotificationKind.CLEANING_CANCELLED: {
        "de": (
            "Stornierung – dieser Reinigungsauftrag entfällt.\n\n"
            "Unterkunft: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Gast: {{4}}\n"
            "Buchungsnummer: {{5}}\n\n"
            "Bitte für diese Wohnung keine Reinigung mehr einplanen. Danke!"
        ),
        "en": (
            "Cancellation – this cleaning assignment is no longer needed.\n\n"
            "Property: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Guest: {{4}}\n"
            "Booking reference: {{5}}\n\n"
            "Please do not schedule a cleaning for this unit. Thank you!"
        ),
        "pl": (
            "Anulowanie – to zlecenie sprzątania jest nieaktualne.\n\n"
            "Obiekt: {{1}}\n"
            "Zameldowanie: {{2}}\n"
            "Wymeldowanie: {{3}}\n"
            "Gość: {{4}}\n"
            "Numer rezerwacji: {{5}}\n\n"
            "Prosimy nie planować sprzątania tego lokalu. Dziękujemy!"
        ),
        "it": (
            "Cancellazione – questo incarico di pulizia non è più necessario.\n\n"
            "Struttura: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Ospite: {{4}}\n"
            "Riferimento prenotazione: {{5}}\n\n"
            "Non programmare pulizie per questa unità. Grazie!"
        ),
        "es": (
            "Cancelación – esta tarea de limpieza ya no es necesaria.\n\n"
            "Alojamiento: {{1}}\n"
            "Entrada: {{2}}\n"
            "Salida: {{3}}\n"
            "Huésped: {{4}}\n"
            "Referencia de reserva: {{5}}\n\n"
            "Por favor, no programe limpieza para esta unidad. ¡Gracias!"
        ),
    },
    NotificationKind.CLEANING_REMINDER: {
        "de": (
            "Erinnerung: morgen steht eine Reinigung an.\n\n"
            "Unterkunft: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Gast: {{4}}\n"
            "Buchungsnummer: {{5}}\n\n"
            "Bitte die Reinigung rechtzeitig einplanen. Danke!"
        ),
        "en": (
            "Reminder: a cleaning is due tomorrow.\n\n"
            "Property: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Guest: {{4}}\n"
            "Booking reference: {{5}}\n\n"
            "Please schedule the cleaning in time. Thank you!"
        ),
        "pl": (
            "Przypomnienie: jutro zaplanowane sprzatanie.\n\n"
            "Obiekt: {{1}}\n"
            "Zameldowanie: {{2}}\n"
            "Wymeldowanie: {{3}}\n"
            "Gosc: {{4}}\n"
            "Numer rezerwacji: {{5}}\n\n"
            "Prosimy zaplanowac sprzatanie na czas. Dziekujemy!"
        ),
        "it": (
            "Promemoria: domani e prevista una pulizia.\n\n"
            "Struttura: {{1}}\n"
            "Check-in: {{2}}\n"
            "Check-out: {{3}}\n"
            "Ospite: {{4}}\n"
            "Riferimento prenotazione: {{5}}\n\n"
            "Pianifica la pulizia per tempo. Grazie!"
        ),
        "es": (
            "Recordatorio: manana hay una limpieza prevista.\n\n"
            "Alojamiento: {{1}}\n"
            "Entrada: {{2}}\n"
            "Salida: {{3}}\n"
            "Huesped: {{4}}\n"
            "Referencia de reserva: {{5}}\n\n"
            "Programa la limpieza a tiempo. Gracias!"
        ),
    },
    NotificationKind.BOOKING_STATUS_NOTICE: {
        "de": (
            "Buchungsupdate: {{1}}\n\nUnterkunft: {{2}}\nCheck-in: {{3}}\n"
            "Check-out: {{4}}\nGast: {{5}}\nBuchung: {{6}}"
        ),
        "en": (
            "Booking update: {{1}}\n\nProperty: {{2}}\nCheck-in: {{3}}\n"
            "Check-out: {{4}}\nGuest: {{5}}\nBooking: {{6}}"
        ),
        "pl": (
            "Aktualizacja rezerwacji: {{1}}\n\nObiekt: {{2}}\nZameldowanie: {{3}}\n"
            "Wymeldowanie: {{4}}\nGość: {{5}}\nRezerwacja: {{6}}"
        ),
        "it": (
            "Aggiornamento prenotazione: {{1}}\n\nStruttura: {{2}}\nCheck-in: {{3}}\n"
            "Check-out: {{4}}\nOspite: {{5}}\nPrenotazione: {{6}}"
        ),
        "es": (
            "Actualización de reserva: {{1}}\n\nAlojamiento: {{2}}\nEntrada: {{3}}\n"
            "Salida: {{4}}\nHuésped: {{5}}\nReserva: {{6}}"
        ),
    },
    NotificationKind.BOOKING_GUEST_INQUIRY: {
        "de": (
            "{{1}}\n\nUnterkunft: {{2}}\nBuchung: {{3}}\nCheck-in: {{4}}\n"
            "Check-out: {{5}}\nGast: {{6}}"
        ),
        "en": (
            "{{1}}\n\nProperty: {{2}}\nBooking: {{3}}\nCheck-in: {{4}}\n"
            "Check-out: {{5}}\nGuest: {{6}}"
        ),
        "pl": (
            "{{1}}\n\nObiekt: {{2}}\nRezerwacja: {{3}}\nZameldowanie: {{4}}\n"
            "Wymeldowanie: {{5}}\nGość: {{6}}"
        ),
        "it": (
            "{{1}}\n\nStruttura: {{2}}\nPrenotazione: {{3}}\nCheck-in: {{4}}\n"
            "Check-out: {{5}}\nOspite: {{6}}"
        ),
        "es": (
            "{{1}}\n\nAlojamiento: {{2}}\nReserva: {{3}}\nEntrada: {{4}}\n"
            "Salida: {{5}}\nHuésped: {{6}}"
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

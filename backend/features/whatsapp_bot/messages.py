"""Nachrichten-Templates des WhatsApp-Bots (deterministisch, keine LLM-Texte).

Formatierungsregeln (Spec): Emoji-Anker, wichtige Werte *fett*, max. ~10
Zeilen, Buttons max. 20 Zeichen. Nutzereingaben werden nur als Werte
eingesetzt, nie als Instruktion interpretiert.
"""

from __future__ import annotations

from datetime import date

from backend.features.cleaning.export import status_label
from backend.features.cleaning.models import CleaningPartner, CleaningTask
from backend.features.whatsapp_bot.dates import format_date

_MAX_LIST_ITEMS = 10


def welcome(name: str, role: str) -> str:
    """Begrüßung mit Fähigkeiten-Überblick."""
    if role == "cleaner":
        return (
            f"\U0001f44b Hallo *{name}*!\n\n"
            "Ich schicke dir deine Putztermine.\n"
            'Schreib mir z. B.: _"Meine Termine nächste Woche"_'
        )
    return (
        f"\U0001f44b Hallo *{name}*!\n\n"
        "Das kann ich für dich tun:\n"
        "\U0001f9f9 Putzpläne erstellen\n"
        "\U0001f4c5 Buchungen anzeigen\n"
        "\U0001f465 Mitarbeiter verwalten\n"
        "\U0001f3e0 Objekte verwalten\n\n"
        'Schreib mir einfach, z. B.:\n_"Putzplan für nächste Woche"_'
    )


def unknown_number() -> str:
    """Höfliche Ablehnung nicht zugeordneter Nummern."""
    return (
        "\U0001f44b Hallo! Deine Nummer ist noch keinem Konto zugeordnet.\n"
        "Bitte wende dich an deinen Gastgeber oder Administrator."
    )


def permission_denied() -> str:
    """Rollen-Verstoß — freundlich, ohne Stacktrace."""
    return (
        "\U0001f512 Dafür fehlt dir leider die Berechtigung.\n"
        "Bitte wende dich an deinen Administrator."
    )


def clarification(question: str) -> str:
    """Rückfrage bei unklarem Intent oder fehlenden Pflichtfeldern."""
    return f"\u2753 {question}"


def error_generic() -> str:
    """Interner Fehler — keine Details nach außen."""
    return (
        "\u26a0\ufe0f Da ist etwas schiefgelaufen. "
        "Bitte versuch es gleich noch einmal."
    )


def putzplan_summary(
    tasks: list[CleaningTask],
    *,
    start: date,
    end: date,
) -> str:
    """Zusammenfassung eines erstellten Putzplans."""
    if not tasks:
        return (
            f"\U0001f9f9 *Putzplan {format_date(start)} – {format_date(end)}*\n\n"
            "\u2705 Keine Reinigungen in diesem Zeitraum."
        )
    properties = {t.property_name for t in tasks if t.property_name}
    week = start.isocalendar()[1]
    return (
        f"\U0001f9f9 *Putzplan KW {week}*\n"
        f"\U0001f4c6 {format_date(start)} – {format_date(end)}\n\n"
        f"\u2705 *{len(tasks)} Reinigungen* geplant\n"
        f"\U0001f3e0 {len(properties)} Objekte\n\n"
        "\U0001f4ce Die Excel-Datei kommt gleich als Anhang."
    )


def putzplan_tasks_list(
    tasks: list[CleaningTask],
    partners_by_id: dict[str, CleaningPartner],
) -> str:
    """Kompakte Terminliste (max. 10 Einträge)."""
    lines = []
    for task in tasks[:_MAX_LIST_ITEMS]:
        partner = partners_by_id.get(task.partner_id or "")
        who = f" → {partner.name}" if partner else ""
        lines.append(
            f"\U0001f9fd {format_date(task.cleaning_date)} "
            f"*{task.property_name or '—'}*{who}"
        )
    if len(tasks) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(tasks) - _MAX_LIST_ITEMS} weitere")
    return "\n".join(lines)


def bookings_list(
    bookings: list[tuple[str, str, date | None, date | None, str | None]],
    *,
    start: date,
    end: date,
) -> str:
    """Buchungsliste: (booking_ref, gast, check_in, check_out, objekt)."""
    header = f"\U0001f4c5 *Buchungen {format_date(start)} – {format_date(end)}*\n"
    if not bookings:
        return header + "\nKeine Buchungen in diesem Zeitraum."
    lines = [header]
    for ref, guest, check_in, check_out, prop in bookings[:_MAX_LIST_ITEMS]:
        prop_part = f" \U0001f3e0 {prop}" if prop else ""
        lines.append(
            f"\U0001f6ce\ufe0f *{guest}*{prop_part}\n"
            f"   {format_date(check_in)} → {format_date(check_out)}"
            f"{f' (Ref: {ref})' if ref else ''}"
        )
    if len(bookings) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(bookings) - _MAX_LIST_ITEMS} weitere")
    return "\n".join(lines)


def booking_details(
    *,
    ref: str,
    guest_name: str,
    property_name: str,
    check_in: date | None,
    check_out: date | None,
    price: float | None,
    platform: str | None,
) -> str:
    """Detailkarte einer Buchung."""
    price_line = f"\U0001f4b6 Preis: *{price:.2f} €*\n" if price else ""
    source_line = f"\U0001f4e7 Quelle: {platform}\n" if platform else ""
    return (
        f"\U0001f4c5 *Buchung {ref}*\n\n"
        f"\U0001f464 Gast: *{guest_name}*\n"
        f"\U0001f3e0 Objekt: *{property_name}*\n"
        f"\U0001f6ec Check-in: *{format_date(check_in)}*\n"
        f"\U0001f6eb Check-out: *{format_date(check_out)}*\n"
        f"{price_line}{source_line}"
    ).rstrip()


def employee_confirm(name: str, phone: str, properties: list[str]) -> str:
    """Bestätigungsdialog: Mitarbeiter anlegen."""
    props = ", ".join(properties) if properties else "—"
    return (
        "\U0001f465 *Neuen Mitarbeiter anlegen?*\n\n"
        f"\U0001f4db Name: *{name}*\n"
        f"\U0001f4f1 Nummer: *{phone}*\n"
        f"\U0001f396\ufe0f Rolle: *Reinigungskraft*\n"
        f"\U0001f3e0 Objekte: {props}"
    )


def employee_deactivate_confirm(name: str) -> str:
    """Bestätigungsdialog: Mitarbeiter deaktivieren."""
    return f"\U0001f465 *Mitarbeiter deaktivieren?*\n\n\U0001f4db Name: *{name}*"


def employee_list(partners: list[CleaningPartner]) -> str:
    """Mitarbeiterliste."""
    if not partners:
        return "\U0001f465 *Mitarbeiter*\n\nNoch keine Mitarbeiter angelegt."
    lines = ["\U0001f465 *Mitarbeiter*\n"]
    for partner in partners[:_MAX_LIST_ITEMS]:
        state = "\u2705" if partner.active else "\u23f8\ufe0f"
        phone = f" ({partner.phone})" if partner.phone else ""
        props = (
            f"\n   \U0001f3e0 {', '.join(partner.property_names)}"
            if partner.property_names
            else ""
        )
        lines.append(f"{state} *{partner.name}*{phone}{props}")
    if len(partners) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(partners) - _MAX_LIST_ITEMS} weitere")
    return "\n".join(lines)


def property_confirm(name: str) -> str:
    """Bestätigungsdialog: Objekt anlegen."""
    return f"\U0001f3e0 *Neues Objekt anlegen?*\n\n\U0001f4db Name: *{name}*"


def property_assign_confirm(employee: str, property_name: str) -> str:
    """Bestätigungsdialog: Objekt zuweisen."""
    return (
        "\U0001f517 *Objekt zuweisen?*\n\n"
        f"\U0001f465 Mitarbeiter: *{employee}*\n"
        f"\U0001f3e0 Objekt: *{property_name}*"
    )


def property_list(names: list[str]) -> str:
    """Objektliste."""
    if not names:
        return "\U0001f3e0 *Objekte*\n\nNoch keine Objekte angelegt."
    lines = ["\U0001f3e0 *Objekte*\n"]
    lines += [f"\U0001f3e0 *{name}*" for name in names[:_MAX_LIST_ITEMS]]
    if len(names) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(names) - _MAX_LIST_ITEMS} weitere")
    return "\n".join(lines)


def action_confirmed(summary: str) -> str:
    """Erfolgsmeldung nach bestätigter Aktion."""
    return f"\u2705 {summary}"


def action_cancelled() -> str:
    """Abbruchmeldung."""
    return "\u274c Abgebrochen. Nichts wurde geändert."


def status_line(task: CleaningTask) -> str:
    """Kurzstatus eines Putzauftrags."""
    return f"{format_date(task.cleaning_date)}: {status_label(task.status)}"

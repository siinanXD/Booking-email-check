"""Putzplan-Nachrichten des WhatsApp-Bots (deterministisch, keine LLM-Texte).

Ausgelagert aus ``messages.py`` (300-Zeilen-Limit). Gleiche Formatierungs-
regeln: Emoji-Anker, wichtige Werte *fett*, max. ~10 Zeilen.
"""

from __future__ import annotations

from datetime import date

from backend.features.cleaning.models import (
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.whatsapp_bot.dates import (
    format_date,
    is_calendar_week,
    period_heading,
)

_MAX_LIST_ITEMS = 10


def putzplan_summary(
    tasks: list[CleaningTask],
    *,
    start: date,
    end: date,
    cancelled: int = 0,
) -> str:
    """Zusammenfassung eines erstellten Putzplans.

    ``cancelled`` zählt stornierte Aufträge im Zeitraum. Sie werden genannt
    statt verschwiegen — sonst liest der Kunde "da fehlt eine Buchung",
    wo in Wahrheit ein Storno vorliegt.
    """
    # Das Kriterium gehoert sichtbar dazu: gelistet wird nach Putztermin
    # (= Abreise + Offset), nicht nach Anreise. Ohne diesen Hinweis wirken
    # Buchungen, die kurz hinter dem Zeitraum abreisen, wie verschluckt.
    # Bei einer KW nennt die Ueberschrift nur die Nummer - dann gehoeren
    # die konkreten Tage darunter. Steht der Bereich schon im Titel, nicht.
    period = (
        f"\U0001f4c6 {format_date(start)} – {format_date(end)}\n"
        if is_calendar_week(start, end)
        else ""
    )
    basis = "\U0001f6eb Grundlage: Reinigungen nach Abreise in diesem Zeitraum"
    if not tasks:
        storno_solo = (
            f"❌ {cancelled} stornierte Buchung"
            f"{'en' if cancelled != 1 else ''} im Zeitraum (Details im Anhang)\n"
            if cancelled
            else ""
        )
        return (
            f"\U0001f9f9 *Putzplan {period_heading(start, end)}*\n"
            f"{period}\n"
            "✅ Keine Reinigungen in diesem Zeitraum.\n"
            f"{storno_solo}"
            f"{basis}"
        )
    storno = (
        f"❌ {cancelled} storniert (im Anhang durchgestrichen)\n" if cancelled else ""
    )
    properties = {t.property_name for t in tasks if t.property_name}
    return (
        f"\U0001f9f9 *Putzplan {period_heading(start, end)}*\n"
        f"{period}\n"
        f"✅ *{len(tasks)} Reinigungen* geplant\n"
        f"{storno}"
        f"\U0001f3e0 {len(properties)} Objekte\n"
        f"{basis}\n\n"
        "\U0001f4ce Die Excel-Datei kommt gleich als Anhang."
    )


def putzplan_tasks_list(
    tasks: list[CleaningTask],
    partners_by_id: dict[str, CleaningPartner],
) -> str:
    """Kompakte Terminliste (max. 10 Einträge); Stornos markiert statt versteckt."""
    lines = []
    for task in tasks[:_MAX_LIST_ITEMS]:
        if task.status == CleaningTaskStatus.CANCELLED:
            lines.append(
                f"❌ {format_date(task.cleaning_date)} "
                f"*{task.property_name or '—'}* — storniert"
            )
            continue
        partner = partners_by_id.get(task.partner_id or "")
        who = f" → {partner.name}" if partner else ""
        lines.append(
            f"\U0001f9fd {format_date(task.cleaning_date)} "
            f"*{task.property_name or '—'}*{who}"
        )
    if len(tasks) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(tasks) - _MAX_LIST_ITEMS} weitere")
    return "\n".join(lines)

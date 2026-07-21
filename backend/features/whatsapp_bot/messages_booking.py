"""Buchungs-Nachrichten des WhatsApp-Bots (Trefferlisten zur Namenssuche).

Eigenes Modul, weil messages.py am 300-Zeilen-Limit sitzt.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from backend.features.whatsapp_bot.dates import format_date

_MAX_LIST_ITEMS = 10


def booking_matches(
    matches: Sequence[tuple[str, str, str, date | None, date | None]],
    *,
    guest_name: str,
) -> str:
    """Mehrere Buchungen zu einem Gastnamen — zur Auswahl auflisten.

    Derselbe Gast kann mehrfach gebucht haben (zwei Zimmer, zwei Aufenthalte).
    Statt willkürlich einen Treffer zu zeigen, listet der Bot alle auf.
    """
    lines = [
        f"\U0001f50d *{len(matches)} Buchungen* für *{guest_name}*\n",
    ]
    for ref, guest, prop, check_in, check_out in matches[:_MAX_LIST_ITEMS]:
        zeitraum = f"{format_date(check_in)} – {format_date(check_out)}"
        lines.append(
            f"\U0001f464 *{guest}*\n"
            f"   \U0001f3e0 {prop or '–'}\n"
            f"   \U0001f4c6 {zeitraum}\n"
            f"   \U0001f516 Nr. {ref or '–'}"
        )
    if len(matches) > _MAX_LIST_ITEMS:
        lines.append(f"... und {len(matches) - _MAX_LIST_ITEMS} weitere")
    lines.append("\nNenn mir die Buchungsnummer.")
    return "\n".join(lines)

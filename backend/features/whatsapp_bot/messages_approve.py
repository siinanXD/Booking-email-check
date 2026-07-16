"""Bestätigungs- und Ergebnismeldungen der Freigabe (deterministisch).

Getrennt von den Anzeige-Texten in ``messages_review``: hier steht, was der
Nutzer VOR einem folgenreichen Klick sieht (wer benachrichtigt wird, welcher
Infotext in den Putzplan geht) und was danach passiert ist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.features.whatsapp_bot.messages_review import _INTENT_SINGULAR

if TYPE_CHECKING:
    from backend.features.whatsapp_bot.review_data import ReviewEntry


def _recipient_line(recipients: list[str]) -> str:
    if not recipients:
        return "\n\nEs wird niemand benachrichtigt."
    who = ", ".join(recipients)
    return f"\n\n\U0001f4f2 Bekommt eine WhatsApp: *{who}*"


def _note_line(note: str | None) -> str:
    """Der Infotext gehört vor den Klick — er landet in Excel und Kalender."""
    if not note:
        return ""
    return f"\n\n\U0001f4dd Infotext für den Putzplan:\n_{note}_"


def approve_confirm(
    entry: ReviewEntry, *, recipients: list[str], note: str | None = None
) -> str:
    """Bestätigungsdialog: einzelne Freigabe."""
    kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
    return (
        f"✅ *Freigeben?*\n\n"
        f"{kind}: *{entry.short_label()}*"
        f"{_note_line(note)}"
        f"{_recipient_line(recipients)}\n"
        "An den Gast geht nichts raus."
    )


def approve_selection_confirm(
    entries: list[ReviewEntry], *, recipients: list[str], note: str | None = None
) -> str:
    """Bestätigungsdialog: mehrere ausgewählte Einträge ("1 und 3 freigeben").

    Die Einträge werden namentlich aufgeführt: Wer per Nummer auswählt, muss vor
    dem Klick sehen, welche Buchungen gemeint sind — eine Zahl allein ist nicht
    nachprüfbar. Ein Infotext gilt für alle gewählten Einträge; das steht auch so
    da, damit niemand ihn nur bei der ersten Buchung vermutet.
    """
    lines = [f"✅ *Diese {len(entries)} freigeben?*\n"]
    for entry in entries:
        kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
        lines.append(f"• {kind}: *{entry.short_label()}*")
    note_block = _note_line(note)
    if note_block and len(entries) > 1:
        note_block += "\n(gilt für alle oben genannten)"
    return "".join(
        [
            "\n".join(lines),
            note_block,
            _recipient_line(recipients),
            "\nAn den Gast geht nichts raus.",
        ]
    )


def approve_all_confirm(entries: list[ReviewEntry], *, recipients: list[str]) -> str:
    """Bestätigungsdialog: Sammelfreigabe."""
    return (
        f"✅ *Alle {len(entries)} freigeben?*"
        f"{_recipient_line(recipients)}\n"
        "An die Gäste geht nichts raus."
    )


def approved(
    done: int, failed: int, *, note_wanted: bool = False, noted: int = 0
) -> str:
    """Ergebnismeldung."""
    tail = _noted_suffix(done, noted) if note_wanted else ""
    if done and not failed:
        suffix = "Eintrag freigegeben." if done == 1 else "Einträge freigegeben."
        return f"✅ {done} {suffix}{tail}"
    if done and failed:
        return f"⚠️ {done} freigegeben, {failed} fehlgeschlagen.{tail}"
    return "⚠️ Freigabe fehlgeschlagen. Bitte in der Weboberfläche prüfen."


def _noted_suffix(done: int, noted: int) -> str:
    """Sagt, wo der Infotext gelandet ist — und wo nicht.

    Nur aufrufen, wenn überhaupt einer gewünscht war. Ohne Putzauftrag (Storno,
    Putzplan nicht gebucht) gibt es keinen Ort für die Bemerkung. Das still zu
    schlucken wäre die schlechtere Variante: der Text wäre weg, ohne dass es
    jemand merkt.
    """
    if noted and noted == done:
        return "\n\U0001f4dd Infotext steht im Putzplan."
    if noted:
        return f"\n\U0001f4dd Infotext steht bei {noted} von {done} im Putzplan."
    return (
        "\n⚠️ Infotext konnte nirgends hinterlegt werden — "
        "zu diesen Einträgen gibt es keinen Putzauftrag."
    )


def too_many(count: int) -> str:
    """Sammelfreigabe über dem Limit."""
    return (
        f"⚠️ {count} Einträge sind mir für eine Sammelfreigabe zu viele.\n"
        "Bitte grenz die Liste ein oder nutz die Weboberfläche."
    )

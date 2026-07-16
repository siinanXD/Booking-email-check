"""Nachrichten-Templates des Chat-Reviews (deterministisch, keine LLM-Texte)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.features.whatsapp_bot.dates import format_date

if TYPE_CHECKING:
    from backend.features.whatsapp_bot.review_data import ReviewEntry

_MAX_LIST_ITEMS = 10
_DRAFT_PREVIEW_CHARS = 600
# Grosszügiger als der Entwurf: die Gastfrage ist der Anlass und meist kurz —
# sie abzuschneiden würde genau die Information kosten, um die es geht.
_MESSAGE_PREVIEW_CHARS = 900

# Anzeigenamen der Intents (Reihenfolge = Reihenfolge in der Übersicht).
_INTENT_LABELS: list[tuple[str, str]] = [
    ("new_booking", "Neue Buchungen"),
    ("cancellation", "Stornos"),
    ("change", "Änderungen"),
    ("guest_inquiry", "Gastnachrichten"),
    ("complaint", "Beschwerden"),
]

_INTENT_SINGULAR = {
    "new_booking": "Neue Buchung",
    "cancellation": "Storno",
    "change": "Änderung",
    "guest_inquiry": "Gastnachricht",
    "complaint": "Beschwerde",
}

# Umgangssprache → Intent-Slug. Der Parser liefert idealerweise den Slug,
# aber "buchungen"/"stornos" o. ä. sollen ebenfalls greifen.
_INTENT_ALIASES = {
    "new_booking": "new_booking",
    "buchung": "new_booking",
    "buchungen": "new_booking",
    "neue buchungen": "new_booking",
    "cancellation": "cancellation",
    "storno": "cancellation",
    "stornos": "cancellation",
    "stornierungen": "cancellation",
    "change": "change",
    "aenderung": "change",
    "änderung": "change",
    "änderungen": "change",
    "guest_inquiry": "guest_inquiry",
    "gastnachricht": "guest_inquiry",
    "gastnachrichten": "guest_inquiry",
    "complaint": "complaint",
    "beschwerde": "complaint",
    "beschwerden": "complaint",
}


def normalize_intent(raw: str | None) -> str | None:
    """Freitext/Slug → Intent-Slug; None wenn kein Filter gemeint ist."""
    if not raw or not raw.strip():
        return None
    return _INTENT_ALIASES.get(raw.strip().lower())


def review_unavailable() -> str:
    """Review-Zugriff ist in diesem Setup nicht verdrahtet."""
    return (
        "⚠️ Das Review ist über den Chat gerade nicht verfügbar.\n"
        "Bitte nutz die Weboberfläche."
    )


def nothing_pending() -> str:
    """Leere Warteschlange."""
    return "✅ *Review*\n\nNichts zu prüfen — alles abgearbeitet."


def overview(entries: list[ReviewEntry]) -> str:
    """Zählung nach Intent."""
    if not entries:
        return nothing_pending()
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.intent or "sonstige"] = (
            counts.get(entry.intent or "sonstige", 0) + 1
        )
    lines = [f"\U0001f4cb *Review* — {len(entries)} offen\n"]
    for slug, label in _INTENT_LABELS:
        if counts.get(slug):
            lines.append(f"• {counts[slug]} {label}")
    rest = sum(v for k, v in counts.items() if k not in dict(_INTENT_LABELS))
    if rest:
        lines.append(f"• {rest} Sonstige")
    lines.append('\nZ. B.: _"Zeig mir alle neuen Buchungen"_')
    return "\n".join(lines)


def listing(entries: list[ReviewEntry], *, intent_filter: str | None = None) -> str:
    """Nummerierte Liste (max. 10)."""
    if not entries:
        return nothing_pending()
    slug = normalize_intent(intent_filter)
    title = dict(_INTENT_LABELS).get(slug or "", "Review") if slug else "Review"
    lines = [f"\U0001f4cb *{title}* — {len(entries)} offen\n"]
    for number, entry in enumerate(entries[:_MAX_LIST_ITEMS], start=1):
        kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
        flag = " ⚠️" if entry.grounding_flag else ""
        prop = f"\n   \U0001f3e0 {entry.property_name}" if entry.property_name else ""
        dates = ""
        if entry.check_in or entry.check_out:
            dates = (
                f"\n   \U0001f4c6 {format_date(entry.check_in)}"
                f" → {format_date(entry.check_out)}"
            )
        lines.append(
            f"*{number}.* {kind}{flag}\n"
            f"   \U0001f464 {entry.guest_name or 'Unbekannt'}{prop}{dates}"
        )
    if len(entries) > _MAX_LIST_ITEMS:
        lines.append(f"… und {len(entries) - _MAX_LIST_ITEMS} weitere")
    lines.append('\nZ. B.: _"Zeig mir Buchung 1"_ oder _"Buchung 1 freigeben"_')
    return "\n".join(lines)


def _quoted_message(entry: ReviewEntry) -> str:
    """Gasttext gekürzt und zitiert — leer, wenn es keinen gibt.

    Kürzen gehört hierher und nicht in die Aufrufer: WhatsApp hat ein
    Textlimit, und ein ungekürzt durchgereichter Gasttext würde die Nachricht
    sprengen statt sie nur abzuschneiden.
    """
    text = (entry.guest_message or "").strip()
    if not text:
        return ""
    if len(text) > _MESSAGE_PREVIEW_CHARS:
        text = text[:_MESSAGE_PREVIEW_CHARS].rstrip() + " …"
    # WhatsApp-Zitat: '> ' macht den fremden Text als solchen kenntlich.
    return "\n".join(f"> {line}" if line.strip() else ">" for line in text.splitlines())


def _message_block(entry: ReviewEntry) -> str:
    """Die Nachricht des Gastes — vor dem Entwurf.

    Sie ist der Anlass und steht deshalb über der Antwort: ohne sie liest man
    einen Entwurf, ohne die Frage zu kennen, auf die er antwortet.
    """
    quoted = _quoted_message(entry)
    if not quoted:
        return ""
    return f"\n\n\U0001f4ac *Nachricht vom Gast:*\n{quoted}"


def details(entry: ReviewEntry) -> str:
    """Detailkarte inklusive Gastnachricht und Antwortentwurf."""
    kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
    ref = f"\n\U0001f516 Ref: *{entry.booking_number}*" if entry.booking_number else ""
    prop = (
        f"\n\U0001f3e0 Objekt: *{entry.property_name}*" if entry.property_name else ""
    )
    dates = ""
    if entry.check_in or entry.check_out:
        dates = (
            f"\n\U0001f4c6 {format_date(entry.check_in)}"
            f" → {format_date(entry.check_out)}"
        )
    flag = "\n⚠️ Grounding-Hinweis: bitte genau prüfen" if entry.grounding_flag else ""
    draft = entry.draft_body.strip() or "(kein Entwurf)"
    if len(draft) > _DRAFT_PREVIEW_CHARS:
        draft = draft[:_DRAFT_PREVIEW_CHARS] + " …"
    return (
        f"\U0001f4cb *{kind}*\n"
        f"\U0001f464 Gast: *{entry.guest_name or 'Unbekannt'}*"
        f"{prop}{dates}{ref}{flag}"
        f"{_message_block(entry)}\n\n"
        f"✍️ *Entwurf:*\n{draft}"
    )


def guest_message(entry: ReviewEntry) -> str:
    """Nur die Nachricht des Gastes ("Nachricht zu Buchung 1")."""
    quoted = _quoted_message(entry)
    if not quoted:
        return (
            f"\U0001f4ac *{entry.short_label()}*\n\n"
            "Zu diesem Eintrag gibt es keine Nachricht vom Gast — "
            "die Mail enthält nur Buchungsdaten."
        )
    return f"\U0001f4ac *Nachricht von {entry.guest_name or 'Gast'}*\n\n{quoted}"


def _recipient_line(recipients: list[str]) -> str:
    if not recipients:
        return "\n\nEs wird niemand benachrichtigt."
    who = ", ".join(recipients)
    return f"\n\n\U0001f4f2 Bekommt eine WhatsApp: *{who}*"


def approve_confirm(entry: ReviewEntry, *, recipients: list[str]) -> str:
    """Bestätigungsdialog: einzelne Freigabe."""
    kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
    return (
        f"✅ *Freigeben?*\n\n"
        f"{kind}: *{entry.short_label()}*"
        f"{_recipient_line(recipients)}\n"
        "An den Gast geht nichts raus."
    )


def approve_selection_confirm(
    entries: list[ReviewEntry], *, recipients: list[str]
) -> str:
    """Bestätigungsdialog: mehrere ausgewählte Einträge ("1 und 3 freigeben").

    Die Einträge werden namentlich aufgeführt: Wer per Nummer auswählt, muss vor
    dem Klick sehen, welche Buchungen gemeint sind — eine Zahl allein ist nicht
    nachprüfbar.
    """
    lines = [f"✅ *Diese {len(entries)} freigeben?*\n"]
    for entry in entries:
        kind = _INTENT_SINGULAR.get(entry.intent or "", "Eintrag")
        lines.append(f"• {kind}: *{entry.short_label()}*")
    return "".join(
        [
            "\n".join(lines),
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


def approved(done: int, failed: int) -> str:
    """Ergebnismeldung."""
    if done and not failed:
        suffix = "Eintrag freigegeben." if done == 1 else "Einträge freigegeben."
        return f"✅ {done} {suffix}"
    if done and failed:
        return f"⚠️ {done} freigegeben, {failed} fehlgeschlagen."
    return "⚠️ Freigabe fehlgeschlagen. Bitte in der Weboberfläche prüfen."


def which_entry() -> str:
    """Rückfrage: keine Position genannt."""
    return (
        "❓ Welchen Eintrag meinst du? Nenn mir die Nummer aus der Liste, "
        'z. B. _"Buchung 1 freigeben"_.'
    )


def position_out_of_range(position: int, total: int) -> str:
    """Rückfrage: Nummer außerhalb der Liste."""
    if total == 0:
        return nothing_pending()
    return f"❓ Es gibt keine Nummer *{position}* — die Liste hat {total} Einträge."


def unknown_booking(ref: str) -> str:
    """Rückfrage: Buchungsnummer nicht in der Warteschlange."""
    return f"❓ Ich habe keine wartende Buchung *{ref}* gefunden."


def too_many(count: int) -> str:
    """Sammelfreigabe über dem Limit."""
    return (
        f"⚠️ {count} Einträge sind mir für eine Sammelfreigabe zu viele.\n"
        "Bitte grenz die Liste ein oder nutz die Weboberfläche."
    )

"""Review-Einträge für den Chat laden und Positionen auflösen.

Ein ReviewRecord trägt nur correlation_id, Entwurf und Intent. Für eine
lesbare Chat-Liste werden die Buchungsdaten aus den Extraktionen ergänzt
(ein Batch-Lookup, kein N+1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.features.whatsapp_bot import messages_review
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.models import ResolvedSender, UserIntent

_MAX_ENTRIES = 50


@dataclass
class ReviewEntry:
    """Ein wartender Review-Eintrag, angereichert um Buchungsdaten."""

    correlation_id: str
    intent: str | None
    draft_body: str
    grounding_flag: bool
    guest_name: str | None = None
    property_name: str | None = None
    booking_number: str | None = None
    check_in: date | None = None
    check_out: date | None = None

    def short_label(self) -> str:
        """Kurzbezeichnung für Bestätigungen und Audit."""
        parts = [self.guest_name or "Unbekannt"]
        if self.property_name:
            parts.append(self.property_name)
        return " · ".join(parts)


def load_entries(
    deps: BotDeps,
    account_id: str,
    *,
    intent_filter: str | None = None,
) -> list[ReviewEntry]:
    """Wartende Reviews, optional nach Intent gefiltert (stabile Reihenfolge)."""
    if deps.review_repo is None:
        return []
    records = deps.review_repo.list_pending(_MAX_ENTRIES, account_id=account_id)
    wanted = messages_review.normalize_intent(intent_filter)
    if wanted is not None:
        records = [r for r in records if r.intent == wanted]
    if not records:
        return []
    extractions = deps.extraction_repo.map_by_correlation_ids(
        [r.correlation_id for r in records], account_id=account_id
    )
    entries = []
    for record in records:
        extraction = extractions.get(record.correlation_id)
        entries.append(
            ReviewEntry(
                correlation_id=record.correlation_id,
                intent=record.intent,
                draft_body=record.draft_body,
                grounding_flag=record.grounding_flag,
                guest_name=getattr(extraction, "guest_name", None),
                property_name=getattr(extraction, "property_name", None),
                booking_number=getattr(extraction, "booking_number", None),
                check_in=getattr(extraction, "check_in", None),
                check_out=getattr(extraction, "check_out", None),
            )
        )
    return entries


def resolve_position(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> tuple[ReviewEntry | None, str | None]:
    """Position bzw. Buchungsnummer → Eintrag. Zweitwert ist die Fehlermeldung.

    Die Nummer bezieht sich auf die zuletzt gezeigte Liste. Gibt es keine,
    wird die aktuelle Warteschlange genommen — dann aber ohne Intent-Filter,
    weil ohne Auflistung kein Kontext existiert.
    """
    listing = deps.conversation_repo.get_last_listing(
        account_id=sender.account_id, wa_id=sender.wa_id
    )
    entries = load_entries(deps, sender.account_id)
    by_id = {e.correlation_id: e for e in entries}

    if intent.booking_ref:
        for entry in entries:
            if entry.booking_number == intent.booking_ref:
                return entry, None
        return None, messages_review.unknown_booking(intent.booking_ref)

    position = intent.position
    if position is None or position < 1:
        return None, messages_review.which_entry()

    ordered = [by_id[cid] for cid in listing if cid in by_id] or entries
    if position > len(ordered):
        return None, messages_review.position_out_of_range(position, len(ordered))
    return ordered[position - 1], None

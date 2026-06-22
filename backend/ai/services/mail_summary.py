"""Kurztext und Stimmung für Mail-Detail."""

from __future__ import annotations

import re

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import StoredEmail
from backend.core.models.mail_summary import MailSummary
from backend.infrastructure.repositories.mail_summary_repository import (
    MailSummaryRepository,
)

_POSITIVE = re.compile(r"\b(danke|freuen|willkommen|bestätigt)\b", re.I)
_NEGATIVE = re.compile(r"\b(beschwerde|storno|problem|ärger|unzufrieden)\b", re.I)


class MailSummaryService:
    """Heuristische Zusammenfassung; optional später LLM."""

    def __init__(self, repo: MailSummaryRepository) -> None:
        self._repo = repo

    def get_or_create(
        self,
        email: StoredEmail,
        extraction: BookingExtraction | None,
        *,
        account_id: str,
    ) -> MailSummary:
        cached = self._repo.get(email.correlation_id, account_id=account_id)
        if cached is not None:
            return cached
        summary = self._build_heuristic(email, extraction)
        return self._repo.upsert(summary, account_id=account_id)

    def from_cache_or_build(
        self,
        email: StoredEmail,
        extraction: BookingExtraction | None,
        *,
        cached: MailSummary | None,
    ) -> MailSummary:
        """Liefert die Summary ohne Schreib-Round-Trip (für den Lese-Pfad).

        Die Heuristik ist deterministisch und billig (Regex), daher lohnt das
        Persistieren beim Anzeigen nicht – es kostet nur einen Mongo-Write.
        """
        if cached is not None:
            return cached
        return self._build_heuristic(email, extraction)

    def _build_heuristic(
        self,
        email: StoredEmail,
        extraction: BookingExtraction | None,
    ) -> MailSummary:
        intent = extraction.intent if extraction else None
        guest = extraction.guest_name if extraction else None
        booking = extraction.booking_number if extraction else None
        parts: list[str] = []
        if intent == BookingIntent.NEW_BOOKING:
            parts.append("Neue Buchung")
        elif intent == BookingIntent.CANCELLATION:
            parts.append("Stornierung")
        elif intent == BookingIntent.CHANGE:
            parts.append("Buchungsänderung")
        elif intent == BookingIntent.COMPLAINT:
            parts.append("Beschwerde")
        elif intent == BookingIntent.GUEST_INQUIRY:
            parts.append("Gastnachricht")
        else:
            parts.append(email.subject[:120] or "E-Mail")
        if guest:
            parts.append(f"Gast: {guest}")
        if booking:
            parts.append(f"Nr. {booking}")
        body = (email.body_text or "").strip()
        if body:
            snippet = body[:160].replace("\n", " ")
            parts.append(snippet)
        text = " · ".join(parts)
        sentiment = _sentiment(email.body_text or "", intent)
        return MailSummary(
            correlation_id=email.correlation_id,
            summary_text=text[:400],
            sentiment=sentiment,
            source="heuristic",
        )


def _sentiment(body: str, intent: BookingIntent | None) -> str:
    if intent in (BookingIntent.COMPLAINT, BookingIntent.CANCELLATION):
        return "negative"
    if _NEGATIVE.search(body):
        return "negative"
    if _POSITIVE.search(body):
        return "positive"
    return "neutral"

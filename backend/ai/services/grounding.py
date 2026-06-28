"""Grounding-Heuristik für Antwortentwürfe."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from backend.ai.services.retrieval import RetrievalHits
from backend.core.models.response import GeneratedResponse

_BOOKING_REF = re.compile(r"\b[A-Z]{2}\d{3,}\b")
_GUEST_NAME = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+\b",
)
_DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DATE_DE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
_NAME_FALSE_POSITIVES = frozenset(
    {
        "Ihre Buchung",
        "Sehr Geehrte",
        "Sehr Geehrter",
        "Ihr Aufenthalt",
        "Nächste Schritte",
    }
)


@dataclass
class GroundingResult:
    """Ergebnis der Grounding-Prüfung mit Detailinformationen."""

    ok: bool
    failed_fields: list[str] = field(default_factory=list)
    confidence: float = 1.0


class GroundingService:
    """Prüft ob Fakten im Entwurf in den Retrieval-Daten vorkommen."""

    def check(
        self,
        draft: GeneratedResponse,
        hits: RetrievalHits,
    ) -> bool:
        """True wenn keine verdächtigen Referenzen gefunden werden."""
        return self.check_with_detail(draft, hits).ok

    def check_with_detail(
        self,
        draft: GeneratedResponse,
        hits: RetrievalHits,
    ) -> GroundingResult:
        """Prüft Buchungsnummern, Gastnamen und Datumsangaben im Entwurf."""
        body = draft.body
        failed_fields: list[str] = []
        total_checks = 0
        passed_checks = 0

        known_bookings = _known_booking_numbers(hits)
        mentioned_bookings = {m.upper() for m in _BOOKING_REF.findall(body)}
        if mentioned_bookings:
            total_checks += 1
            if known_bookings and mentioned_bookings.issubset(known_bookings):
                passed_checks += 1
            else:
                failed_fields.append("booking_ref")

        if hits.guest and hits.guest.name:
            names_in_draft = [
                name
                for name in _GUEST_NAME.findall(body)
                if name not in _NAME_FALSE_POSITIVES
            ]
            if names_in_draft:
                total_checks += 1
                if all(_name_grounded(n, hits.guest.name) for n in names_in_draft):
                    passed_checks += 1
                else:
                    failed_fields.append("guest_name")

        allowed_dates = _allowed_dates(hits)
        dates_in_draft = _dates_in_text(body)
        if dates_in_draft:
            total_checks += 1
            if allowed_dates and all(d in allowed_dates for d in dates_in_draft):
                passed_checks += 1
            else:
                failed_fields.append("date")

        if total_checks == 0:
            confidence = 1.0
        else:
            confidence = passed_checks / total_checks

        return GroundingResult(
            ok=not failed_fields,
            failed_fields=failed_fields,
            confidence=confidence,
        )


def _known_booking_numbers(hits: RetrievalHits) -> set[str]:
    known: set[str] = set()
    for reservation in hits.reservations or []:
        if reservation.booking_number:
            known.add(reservation.booking_number.upper())
    return known


def _name_grounded(candidate: str, known: str) -> bool:
    candidate_lower = candidate.lower()
    known_lower = known.lower()
    if known_lower in candidate_lower:
        return True
    candidate_tokens = set(candidate_lower.split())
    known_tokens = set(known_lower.split())
    overlap = candidate_tokens & known_tokens
    return len(overlap) >= 2


def _allowed_dates(hits: RetrievalHits) -> set[str]:
    allowed: set[str] = set()
    for reservation in hits.reservations or []:
        for field_value in (reservation.check_in, reservation.check_out):
            if isinstance(field_value, date):
                allowed.add(field_value.isoformat())
    return allowed


def sanitize_draft_guest_names(body: str, known_guest: str | None) -> str:
    """Entfernt offensichtliche False-Positive-Gastnamen aus dem Entwurf."""
    if not known_guest or not known_guest.strip():
        return body
    result = body
    for name in _GUEST_NAME.findall(body):
        if name in _NAME_FALSE_POSITIVES:
            continue
        if not _name_grounded(name, known_guest):
            result = result.replace(name, known_guest.strip())
    return result


def cited_span(body: str, booking_number: str | None) -> str | None:
    """Kurze Belegstelle aus der Mail (Highlight in „Warum diese Einstufung?").

    Bevorzugt den Kontext rund um die Buchungsnummer, sonst die erste
    aussagekräftige Zeile.
    """
    text = (body or "").strip()
    if not text:
        return None
    if booking_number:
        idx = text.lower().find(booking_number.lower())
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(booking_number) + 40)
            snippet = text[start:end].strip()
            return f"…{snippet}…" if start > 0 or end < len(text) else snippet
    for line in text.splitlines():
        cleaned = line.strip()
        if len(cleaned) >= 12:
            return cleaned[:160]
    return text[:160]


def _dates_in_text(body: str) -> list[str]:
    dates = list(_DATE_ISO.findall(body))
    for de_date in _DATE_DE.findall(body):
        day, month, year = de_date.split(".")
        dates.append(f"{year}-{month}-{day}")
    return dates

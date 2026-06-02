"""Metadaten-Retrieval (Mongo, kein Vector im Schritt 3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from models.email import StoredEmail
from models.entities import Guest, Reservation
from repositories.email_repository import EmailRepository
from repositories.entity_repository import EntityRepository
from schemas.booking.extraction import BookingExtraction
from services.similarity_search import SimilaritySearchService


@dataclass
class RetrievalHits:
    """Kontext für Antwortgenerierung."""

    guest: Guest | None = None
    reservations: list[Reservation] | None = None
    thread_emails: list[StoredEmail] | None = None
    similar_cases: list[dict[str, object]] = field(default_factory=list)


class RetrievalService:
    """Strukturierte Abfragen über Metadaten."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        email_repo: EmailRepository,
        similarity: SimilaritySearchService | None = None,
    ) -> None:
        self._entities = entity_repo
        self._emails = email_repo
        self._similarity = similarity

    def retrieve(
        self,
        email: StoredEmail,
        extraction: BookingExtraction | None = None,
        include_similar: bool = False,
    ) -> RetrievalHits:
        """Lädt Gast, Reservierungen und Thread-Kontext."""
        guest: Guest | None = None
        reservations: list[Reservation] = []

        if extraction and extraction.email:
            guest = self._entities.get_guest_by_email(extraction.email)
            reservations = self._entities.find_reservations_by_guest_email(
                extraction.email
            )
        if extraction and extraction.booking_number:
            by_number = self._entities.find_reservation_by_booking_number(
                extraction.booking_number
            )
            if by_number and by_number not in reservations:
                reservations.append(by_number)

        thread_ids = email.thread_ids()
        thread_emails: list[StoredEmail] = []
        for tid in thread_ids:
            found = self._emails.get_by_message_id(tid)
            if found:
                thread_emails.append(found)

        if not reservations:
            reservations = self._entities.find_reservations_by_correlation_id(
                email.correlation_id
            )

        similar: list[dict[str, object]] = []
        if include_similar and self._similarity is not None:
            similar = self._similarity.find_similar_cases(email.body_text, limit=3)

        return RetrievalHits(
            guest=guest,
            reservations=reservations or None,
            thread_emails=thread_emails or None,
            similar_cases=similar,
        )

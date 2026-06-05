"""Entity Resolution für Gäste (Relay-Adressen, mehrdeutige Namen)."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.models.entities import Guest
from backend.infrastructure.repositories.entity_repository import EntityRepository

CONFIDENCE_EMAIL_EXACT = 1.0
CONFIDENCE_BOOKING_NUMBER = 0.9
CONFIDENCE_NAME_PLATFORM = 0.7
CONFIDENCE_THRESHOLD = 0.6


class EntityResolutionService:
    """Matcht extrahierte Gastdaten gegen persistierte Entitäten."""

    def __init__(self, entity_repo: EntityRepository) -> None:
        """Initialize the instance with its dependencies."""
        self._entities = entity_repo

    def resolve_guest(
        self,
        extraction: BookingExtraction,
        from_address: str,
        *,
        account_id: str | None = None,
    ) -> tuple[Guest | None, float]:
        """Löst einen Gast mit Konfidenzschwelle auf.

        Priorität: E-Mail (1.0) → Buchungsnummer (0.9) → Name+Plattform (0.7).
        Kein Kandidaten-Vergleich — erster Treffer über Schwelle 0.6 gewinnt.
        Bewusste Entscheidung: Buchungsnummer schlägt Name+Plattform auch bei Konflikt.
        """
        for email in (extraction.email, from_address):
            if not email or "@" not in email:
                continue
            guest = self._entities.get_guest_by_email(
                email.strip().lower(),
                account_id=account_id,
            )
            if guest is not None:
                return guest, CONFIDENCE_EMAIL_EXACT

        if extraction.booking_number:
            reservation = self._entities.find_reservation_by_booking_number(
                extraction.booking_number,
                account_id=account_id,
            )
            if reservation is not None and reservation.guest_id:
                guest = self._entities.get_guest_by_id(
                    reservation.guest_id,
                    account_id=account_id,
                )
                if guest is not None:
                    return guest, CONFIDENCE_BOOKING_NUMBER

        if extraction.guest_name and extraction.platform:
            guests = self._entities.find_guests_by_name_and_platform(
                extraction.guest_name,
                extraction.platform,
                account_id=account_id,
            )
            if guests:
                return guests[0], CONFIDENCE_NAME_PLATFORM

        return None, 0.0

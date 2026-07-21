"""Storno-Logik: bestehenden Auftrag finden, Wiederbelebung begrenzen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.features.cleaning.identity import task_id_for

if TYPE_CHECKING:
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.features.cleaning.models import CleaningTask
    from backend.infrastructure.repositories.cleaning_task_repository import (
        CleaningTaskRepository,
    )


def find_for_cancellation(
    repo: CleaningTaskRepository,
    extraction: BookingExtraction,
    account_id: str,
) -> CleaningTask | None:
    """Den Auftrag zur stornierten Buchung suchen — Buchungsnummer zuerst."""
    if extraction.booking_number:
        by_number = repo.find_by_booking_number(
            extraction.booking_number, account_id=account_id
        )
        if by_number is not None:
            return by_number
    return repo.get(task_id_for(extraction, account_id), account_id=account_id)


def may_reopen(cancelled_at: datetime | None, event_at: datetime | None) -> bool:
    """Darf ein stornierter Auftrag durch dieses Event wieder aktiv werden?

    Nur, wenn das Event nachweislich **nach** dem Storno liegt — also eine echte
    Neubuchung desselben Zeitraums. Ohne Zeitstempel bleibt der Auftrag storniert.

    Hintergrund: Ein erneut verarbeitetes Event ohne diese Prüfung weckte den
    Auftrag wieder auf und benachrichtigte die Putzkraft. Betroffen war jede
    Wiederverarbeitung älterer Mails — insbesondere der Backfill, der beim
    Freischalten des Putzplans sämtliche Bestandsbuchungen erneut durchschiebt
    und stornierte Aufträge damit reihenweise reaktivierte. Die Putzkraft fuhr
    zu einem Zimmer, das nie belegt war.
    """
    if event_at is None:
        return False
    if cancelled_at is None:
        return True
    # Mongo liefert naive Zeitstempel zurück; beide Seiten auf UTC normalisieren,
    # sonst wirft der Vergleich TypeError und der Storno-Schutz fällt aus.
    return _as_utc(event_at) > _as_utc(cancelled_at)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)

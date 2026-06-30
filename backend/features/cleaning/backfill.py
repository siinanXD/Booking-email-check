"""Putzplan-Backfill: erzeugt Aufträge aus bestehenden Extraktionen."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from backend.features.cleaning.models import SOURCE_BACKFILL

if TYPE_CHECKING:
    from backend.features.cleaning.service import CleaningScheduleService
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )


def backfill_account(
    service: CleaningScheduleService,
    account_id: str,
    *,
    today: date,
    extraction_repo: ExtractionRepository,
) -> int:
    """Legt für bestehende, zukünftige Buchungen Aufträge an (ohne WhatsApp)."""
    if not service.is_enabled(account_id):
        return 0
    pairs = extraction_repo.list_future_bookings(
        account_id=account_id, checkout_from=today
    )
    count = 0
    for correlation_id, extraction in pairs:
        service.process_booking_event(
            correlation_id,
            extraction,
            account_id=account_id,
            notify=False,
            source=SOURCE_BACKFILL,
        )
        count += 1
    return count

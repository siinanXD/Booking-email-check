"""Übernahme von Putzaufträgen, die vor der Zimmer-Identität entstanden sind.

Die ``task_id`` enthielt früher kein Zimmer. Bestandsaufträge liegen deshalb
unter einem alten Schlüssel; ohne Übernahme entstünde beim nächsten Mail-Eingang
ein zweiter Auftrag daneben statt einer Aktualisierung.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.features.cleaning.identity import cleaning_task_id

if TYPE_CHECKING:
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.features.cleaning.models import CleaningTask
    from backend.infrastructure.repositories.cleaning_task_repository import (
        CleaningTaskRepository,
    )

logger = logging.getLogger(__name__)


def legacy_task_id(extraction: BookingExtraction, account_id: str) -> str:
    """Der Schlüssel, den derselbe Auftrag vor der Zimmer-Identität hatte."""
    return cleaning_task_id(
        account_id=account_id,
        booking_number=extraction.booking_number,
        property_name=extraction.property_name,
        check_out=extraction.check_out,
        guest_name=extraction.guest_name,
    )


def get_or_adopt(
    repo: CleaningTaskRepository,
    extraction: BookingExtraction,
    account_id: str,
    task_id: str,
) -> CleaningTask | None:
    """Auftrag unter neuem Schlüssel — sonst Übernahme des alten.

    Übernommen wird nur, wenn der Altauftrag dasselbe Zimmer betrifft (oder gar
    keines trägt). Gehört er zum Schwesterzimmer derselben Reservierung, bleibt
    er liegen und wird übernommen, sobald dessen eigene Mail eintrifft.
    """
    existing = repo.get(task_id, account_id=account_id)
    if existing is not None:
        return existing

    legacy_id = legacy_task_id(extraction, account_id)
    if legacy_id == task_id:
        return None  # ohne Zimmerangabe identisch — nichts zu übernehmen
    legacy = repo.get(legacy_id, account_id=account_id)
    if legacy is None:
        return None

    room = (extraction.room_number or "").strip().lower()
    legacy_room = (legacy.room_number or "").strip().lower()
    if legacy_room and legacy_room != room:
        return None  # gehört zum anderen Zimmer der Reservierung

    legacy.task_id = task_id
    legacy.room_number = extraction.room_number or legacy.room_number
    repo.upsert(legacy, account_id=account_id)
    repo.delete(legacy_id, account_id=account_id)
    logger.info(
        "Putzauftrag auf Zimmer-Identität migriert (%s -> %s, Zimmer=%s)",
        legacy_id,
        task_id,
        extraction.room_number or "—",
    )
    return legacy

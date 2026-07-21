"""Putzauftrag beim Erkennen einer Buchung anlegen (nicht erst bei Freigabe).

Ob geputzt werden muss, entscheidet der Check-out der Buchung — nicht, ob der
Antwortentwurf freigegeben wurde. Der Auftrag entsteht deshalb schon im
validate-Schritt. Benachrichtigt werden die Putzpartner erst bei der Freigabe
(finalize), damit kein Versand ohne menschliche Entscheidung passiert.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.features.cleaning.models import SOURCE_BOOKING_EMAIL

if TYPE_CHECKING:
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.core.models.email import StoredEmail
    from backend.features.cleaning.service import CleaningScheduleService

logger = logging.getLogger(__name__)


def schedule_cleaning_on_detect(
    service: CleaningScheduleService | None,
    email: StoredEmail,
    extraction: BookingExtraction,
) -> None:
    """Legt den Putzauftrag ohne Versand an; Fehler brechen den Mail-Workflow nie."""
    if service is None:
        return
    try:
        service.process_booking_event(
            email.correlation_id,
            extraction,
            account_id=email.account_id,
            notify=False,
            source=SOURCE_BOOKING_EMAIL,
            event_at=email.received_at,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Putzplan-Verarbeitung fehlgeschlagen für %s", email.correlation_id
        )

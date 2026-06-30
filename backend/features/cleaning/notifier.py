"""WhatsApp-Versand des Putzplans (an alle aktiven Partner einer Wohnung)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.models.notification import NotificationKind, NotificationStatus
from backend.features.cleaning.models import (
    SOURCE_SYSTEM,
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)

if TYPE_CHECKING:
    from backend.features.notifications.notification_service import NotificationService

# Versand-Status, die als "Nachricht raus" gelten (SENT oder Dry-Run-SKIPPED).
_DELIVERED = (NotificationStatus.SENT, NotificationStatus.SKIPPED)


def in_quiet_window(hour: int, start: int, end: int) -> bool:
    """True, wenn ``hour`` im Sendefenster-Verbot liegt (Wrap-around um Mitternacht).

    ``start == end`` deaktiviert Quiet-Hours komplett.
    """
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    # Über Mitternacht, z. B. 22–7.
    return hour >= start or hour < end


class CleaningNotifier:
    """Kapselt den WhatsApp-Versand an Putzpartner (Fan-out + Status-Spiegelung)."""

    def __init__(
        self,
        notification_service: NotificationService | None,
        partner_repo: CleaningPartnerRepository,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._svc = notification_service
        self._partner_repo = partner_repo

    def partners_for(
        self, property_name: str | None, account_id: str
    ) -> list[CleaningPartner]:
        """Alle aktiven Putzpartner einer Wohnung."""
        return self._partner_repo.find_for_property(
            property_name, account_id=account_id
        )

    def notify(
        self,
        task: CleaningTask,
        extraction: BookingExtraction,
        partners: list[CleaningPartner],
        kind: NotificationKind,
        account_id: str,
        *,
        correlation_id: str,
    ) -> None:
        """Sendet an alle Partner mit Telefon; spiegelt das Ergebnis am Auftrag."""
        if self._svc is None:
            return
        any_sent = False
        any_delivered = False
        last_status: str | None = None
        last_error: str | None = None
        for partner in partners:
            if not partner.phone:
                continue
            record = self._svc.dispatch_to_partner(
                correlation_id,
                extraction,
                kind=kind,
                recipient_e164=partner.phone,
                locale=partner.locale,
                account_id=account_id,
            )
            if record is None:
                continue
            last_status = record.status.value
            last_error = record.error
            if record.status == NotificationStatus.SENT:
                any_sent = True
            if record.status in _DELIVERED:
                any_delivered = True

        if any_delivered:
            task.last_notification_status = (
                NotificationStatus.SENT.value if any_sent else last_status
            )
            task.last_notification_error = None
        elif last_status is not None:
            task.last_notification_status = last_status
            task.last_notification_error = last_error

        if (
            kind == NotificationKind.BOOKING_CLEANING_TASK
            and any_delivered
            and task.status == CleaningTaskStatus.SCHEDULED
        ):
            task.record_status(CleaningTaskStatus.NOTIFIED, source=SOURCE_SYSTEM)

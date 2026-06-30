"""Putzplan-Logik: reagiert auf freigegebene Buchungs-/Storno-Events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.notification import NotificationKind, NotificationStatus
from backend.features.cleaning.identity import cleaning_date_for, cleaning_task_id
from backend.features.cleaning.models import (
    SOURCE_BOOKING_EMAIL,
    SOURCE_CANCELLATION_EMAIL,
    SOURCE_SYSTEM,
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
    PlatformSettingsRepository,
)

if TYPE_CHECKING:
    from backend.features.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Versand-Status, die als "Nachricht raus" gelten (SENT oder Dry-Run-SKIPPED).
_DELIVERED = (NotificationStatus.SENT, NotificationStatus.SKIPPED)
# Intents, die einen Putzauftrag anlegen/aktualisieren (None = wie Neubuchung).
_SCHEDULING_INTENTS = (BookingIntent.NEW_BOOKING, BookingIntent.CHANGE, None)


class CleaningScheduleService:
    """Pflegt Putzaufträge aus dem Buchungs-Workflow."""

    def __init__(
        self,
        partner_repo: CleaningPartnerRepository,
        task_repo: CleaningTaskRepository,
        platform_settings_repo: PlatformSettingsRepository,
        notifier: NotificationService | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._partner_repo = partner_repo
        self._task_repo = task_repo
        self._platform_settings_repo = platform_settings_repo
        self._notifier = notifier

    def is_enabled(self, account_id: str | None) -> bool:
        """True, wenn der Putzplan für den Account freigeschaltet ist."""
        if not account_id:
            return False
        settings = self._platform_settings_repo.get(account_id)
        return settings is not None and settings.feature_enabled(
            FEATURE_CLEANING_SCHEDULE
        )

    def process_booking_event(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        *,
        account_id: str | None = None,
        notify: bool = True,
        source: str = SOURCE_BOOKING_EMAIL,
    ) -> CleaningTask | None:
        """Verarbeitet ein freigegebenes Event, wenn das Feature aktiv ist."""
        if not account_id or not self.is_enabled(account_id):
            return None
        settings = self._platform_settings_repo.get(account_id)
        offset = settings.cleaning_checkout_offset_days if settings else 0
        intent = extraction.intent
        if intent == BookingIntent.CANCELLATION:
            return self._handle_cancellation(
                correlation_id, extraction, account_id, offset, notify=notify
            )
        if intent in _SCHEDULING_INTENTS:
            return self._upsert_task(
                correlation_id,
                extraction,
                account_id,
                offset,
                intent,
                notify=notify,
                source=source,
            )
        return None

    def _identity(self, extraction: BookingExtraction, account_id: str) -> str:
        return cleaning_task_id(
            account_id=account_id,
            booking_number=extraction.booking_number,
            property_name=extraction.property_name,
            check_out=extraction.check_out,
            guest_name=extraction.guest_name,
        )

    def _first_partner(
        self, property_name: str | None, account_id: str
    ) -> CleaningPartner | None:
        partners = self._partner_repo.find_for_property(
            property_name, account_id=account_id
        )
        return partners[0] if partners else None

    def _upsert_task(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        account_id: str,
        offset: int,
        intent: BookingIntent | None,
        *,
        notify: bool = True,
        source: str = SOURCE_BOOKING_EMAIL,
    ) -> CleaningTask:
        """Legt einen Putzauftrag an oder aktualisiert einen bestehenden."""
        task_id = self._identity(extraction, account_id)
        cleaning_date = cleaning_date_for(extraction.check_out, offset)
        partner = self._first_partner(extraction.property_name, account_id)
        existing = self._task_repo.get(task_id, account_id=account_id)
        if existing is not None:
            return self._update_existing(
                existing, extraction, account_id, cleaning_date, partner, intent
            )
        task = CleaningTask(
            task_id=task_id,
            account_id=account_id,
            booking_number=extraction.booking_number,
            correlation_id=correlation_id,
            property_name=extraction.property_name,
            room_number=extraction.room_number,
            guest_name=extraction.guest_name,
            check_in=extraction.check_in,
            check_out=extraction.check_out,
            cleaning_date=cleaning_date,
            partner_id=partner.partner_id if partner else None,
            source_intent=intent.value if intent else None,
        )
        initial = (
            CleaningTaskStatus.SCHEDULED if partner else CleaningTaskStatus.UNASSIGNED
        )
        task.record_status(initial, source=source)
        if notify:
            self._notify_partner(
                task,
                extraction,
                partner,
                NotificationKind.BOOKING_CLEANING_TASK,
                account_id,
            )
        self._task_repo.upsert(task, account_id=account_id)
        logger.info("Putzauftrag angelegt (%s) Status=%s", task_id, task.status.value)
        return task

    def _update_existing(
        self,
        task: CleaningTask,
        extraction: BookingExtraction,
        account_id: str,
        cleaning_date: object,
        partner: CleaningPartner | None,
        intent: BookingIntent | None,
    ) -> CleaningTask:
        """Aktualisiert einen bestehenden Auftrag ohne manuelle Edits zu kippen."""
        if extraction.check_in is not None:
            task.check_in = extraction.check_in
        if extraction.check_out is not None:
            task.check_out = extraction.check_out
        if cleaning_date is not None:
            task.cleaning_date = cleaning_date  # type: ignore[assignment]

        if task.status == CleaningTaskStatus.CANCELLED:
            # Re-Buchung nach Storno: Auftrag wieder aktivieren.
            task.cancelled_at = None
            if partner and not task.partner_id:
                task.partner_id = partner.partner_id
            reopened = (
                CleaningTaskStatus.SCHEDULED
                if task.partner_id
                else CleaningTaskStatus.UNASSIGNED
            )
            task.record_status(
                reopened, source=SOURCE_BOOKING_EMAIL, note="reopened_after_cancel"
            )
        elif not task.manually_edited:
            # Partner nachtragen, falls inzwischen einer hinterlegt wurde.
            if partner and not task.partner_id:
                task.partner_id = partner.partner_id
                if task.status == CleaningTaskStatus.UNASSIGNED:
                    task.record_status(
                        CleaningTaskStatus.SCHEDULED, source=SOURCE_BOOKING_EMAIL
                    )
        task.updated_at = datetime.now(UTC)
        self._task_repo.upsert(task, account_id=account_id)
        return task

    def _handle_cancellation(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        account_id: str,
        offset: int,
        *,
        notify: bool = True,
    ) -> CleaningTask:
        """Storniert den verknüpften Auftrag (oder legt einen Storno-Stub an)."""
        task = self._find_for_cancellation(extraction, account_id)
        if task is None:
            task = CleaningTask(
                task_id=self._identity(extraction, account_id),
                account_id=account_id,
                booking_number=extraction.booking_number,
                correlation_id=correlation_id,
                property_name=extraction.property_name,
                room_number=extraction.room_number,
                guest_name=extraction.guest_name,
                check_in=extraction.check_in,
                check_out=extraction.check_out,
                cleaning_date=cleaning_date_for(extraction.check_out, offset),
                source_intent=BookingIntent.CANCELLATION.value,
            )
        if task.status == CleaningTaskStatus.CANCELLED:
            return task  # idempotent
        task.record_status(
            CleaningTaskStatus.CANCELLED, source=SOURCE_CANCELLATION_EMAIL
        )
        # WhatsApp an den zugeordneten Putzpartner: "Auftrag entfällt".
        if notify:
            partner = self._load_partner(task, account_id)
            self._notify_partner(
                task,
                extraction,
                partner,
                NotificationKind.CLEANING_CANCELLED,
                account_id,
            )
        self._task_repo.upsert(task, account_id=account_id)
        logger.info("Putzauftrag storniert (%s)", task.task_id)
        return task

    def _load_partner(
        self, task: CleaningTask, account_id: str
    ) -> CleaningPartner | None:
        if not task.partner_id:
            return None
        return self._partner_repo.get(task.partner_id, account_id=account_id)

    def _notify_partner(
        self,
        task: CleaningTask,
        extraction: BookingExtraction,
        partner: CleaningPartner | None,
        kind: NotificationKind,
        account_id: str,
    ) -> None:
        """Versendet die Partner-WhatsApp und spiegelt das Ergebnis am Auftrag."""
        if self._notifier is None or partner is None or not partner.phone:
            return
        record = self._notifier.dispatch_to_partner(
            task.correlation_id or "",
            extraction,
            kind=kind,
            recipient_e164=partner.phone,
            locale=partner.locale,
            account_id=account_id,
        )
        if record is None:
            return
        task.last_notification_status = record.status.value
        task.last_notification_error = record.error
        if (
            kind == NotificationKind.BOOKING_CLEANING_TASK
            and record.status in _DELIVERED
            and task.status == CleaningTaskStatus.SCHEDULED
        ):
            task.record_status(CleaningTaskStatus.NOTIFIED, source=SOURCE_SYSTEM)

    def _find_for_cancellation(
        self, extraction: BookingExtraction, account_id: str
    ) -> CleaningTask | None:
        if extraction.booking_number:
            by_number = self._task_repo.find_by_booking_number(
                extraction.booking_number, account_id=account_id
            )
            if by_number is not None:
                return by_number
        return self._task_repo.get(
            self._identity(extraction, account_id), account_id=account_id
        )

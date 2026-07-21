"""Putzplan-Logik: reagiert auf freigegebene Buchungs-/Storno-Events."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.notification import NotificationKind
from backend.features.cleaning.identity import cleaning_date_for, task_id_for
from backend.features.cleaning.master_data import refresh_master_data
from backend.features.cleaning.migration import get_or_adopt
from backend.features.cleaning.models import (
    SOURCE_BOOKING_EMAIL,
    SOURCE_CANCELLATION_EMAIL,
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.cleaning.notifier import CleaningNotifier
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
    from backend.features.billing.entitlement_service import EntitlementService
    from backend.features.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)

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
        entitlement_service: EntitlementService | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._partner_repo = partner_repo
        self._task_repo = task_repo
        self._platform_settings_repo = platform_settings_repo
        self._notifier = CleaningNotifier(notifier, partner_repo)
        self._entitlement_service = entitlement_service

    def is_enabled(self, account_id: str | None) -> bool:
        """True, wenn der Putzplan freigeschaltet ist (Plan-Features ∪ Toggles)."""
        if not account_id:
            return False
        # Gleiche Quelle wie cleaning_queries.feature_enabled – sonst zeigt die
        # UI einen Putzplan, für den nie Aufträge entstehen.
        if self._entitlement_service is not None:
            return FEATURE_CLEANING_SCHEDULE in (
                self._entitlement_service.effective_features(account_id)
            )
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
        task_id = task_id_for(extraction, account_id)
        cleaning_date = cleaning_date_for(extraction.check_out, offset)
        partners = self._notifier.partners_for(extraction.property_name, account_id)
        existing = get_or_adopt(self._task_repo, extraction, account_id, task_id)
        if existing is not None:
            return self._update_existing(
                existing,
                extraction,
                account_id,
                cleaning_date,
                partners,
                intent,
                correlation_id=correlation_id,
                notify=notify,
            )
        primary = partners[0] if partners else None
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
            partner_id=primary.partner_id if primary else None,
            source_intent=intent.value if intent else None,
        )
        initial = (
            CleaningTaskStatus.SCHEDULED if primary else CleaningTaskStatus.UNASSIGNED
        )
        task.record_status(initial, source=source)
        if notify:
            self._notifier.notify(
                task,
                extraction,
                partners,
                NotificationKind.BOOKING_CLEANING_TASK,
                account_id,
                correlation_id=correlation_id,
            )
        self._task_repo.upsert(task, account_id=account_id)
        logger.info("Putzauftrag angelegt (%s) Status=%s", task_id, task.status.value)
        return task

    def _update_existing(
        self,
        task: CleaningTask,
        extraction: BookingExtraction,
        account_id: str,
        cleaning_date: date | None,
        partners: list[CleaningPartner],
        intent: BookingIntent | None,
        *,
        correlation_id: str,
        notify: bool = False,
    ) -> CleaningTask:
        """Aktualisiert einen bestehenden Auftrag ohne manuelle Edits zu kippen."""
        primary = partners[0] if partners else None
        prev_cleaning = task.cleaning_date
        if extraction.check_in is not None:
            task.check_in = extraction.check_in
        if extraction.check_out is not None:
            task.check_out = extraction.check_out
        if cleaning_date is not None:
            task.cleaning_date = cleaning_date
        date_changed = cleaning_date is not None and cleaning_date != prev_cleaning
        refresh_master_data(task, extraction)
        if task.status == CleaningTaskStatus.CANCELLED:
            # Re-Buchung nach Storno: Auftrag wieder aktivieren.
            task.cancelled_at = None
            if primary and not task.partner_id:
                task.partner_id = primary.partner_id
            reopened = (
                CleaningTaskStatus.SCHEDULED
                if task.partner_id
                else CleaningTaskStatus.UNASSIGNED
            )
            task.record_status(
                reopened, source=SOURCE_BOOKING_EMAIL, note="reopened_after_cancel"
            )
        elif not task.manually_edited:
            if primary and not task.partner_id:
                task.partner_id = primary.partner_id
                if task.status == CleaningTaskStatus.UNASSIGNED:
                    task.record_status(
                        CleaningTaskStatus.SCHEDULED, source=SOURCE_BOOKING_EMAIL
                    )
            if (
                intent == BookingIntent.CHANGE
                and date_changed
                and task.status == CleaningTaskStatus.NOTIFIED
            ):
                # Putztermin verschoben → Partner erneut informieren.
                task.record_status(
                    CleaningTaskStatus.NOTIFIED,
                    source=SOURCE_BOOKING_EMAIL,
                    note="date_changed",
                )
                self._notifier.notify(
                    task,
                    extraction,
                    partners,
                    NotificationKind.BOOKING_CLEANING_TASK,
                    account_id,
                    correlation_id=correlation_id,
                )
        if notify:
            self._notifier.notify_once(
                task, extraction, partners, account_id, correlation_id=correlation_id
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
                task_id=task_id_for(extraction, account_id),
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
        if notify:
            partners = self._notifier.partners_for(task.property_name, account_id)
            self._notifier.notify(
                task,
                extraction,
                partners,
                NotificationKind.CLEANING_CANCELLED,
                account_id,
                correlation_id=correlation_id,
            )
        self._task_repo.upsert(task, account_id=account_id)
        logger.info("Putzauftrag storniert (%s)", task.task_id)
        return task

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
            task_id_for(extraction, account_id), account_id=account_id
        )

"""Putz-Erinnerungen: WhatsApp am Vortag an die Partner einer Wohnung."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.models.notification import NotificationKind
from backend.features.cleaning.models import (
    CleaningStatusEvent,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.cleaning.notifier import CleaningNotifier, in_quiet_window
from backend.infrastructure.repositories.account_repository import AccountRepository
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
    from backend.core.config.app_context import AppContext
    from backend.features.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)

_OPEN_STATUSES = (CleaningTaskStatus.SCHEDULED, CleaningTaskStatus.NOTIFIED)


def _extraction_from_task(task: CleaningTask) -> BookingExtraction:
    return BookingExtraction(
        booking_number=task.booking_number,
        property_name=task.property_name,
        room_number=task.room_number,
        guest_name=task.guest_name,
        check_in=task.check_in,
        check_out=task.check_out,
    )


class CleaningReminderService:
    """Findet Aufträge mit Putztermin morgen und erinnert die Partner."""

    def __init__(
        self,
        account_repo: AccountRepository,
        task_repo: CleaningTaskRepository,
        partner_repo: CleaningPartnerRepository,
        platform_settings_repo: PlatformSettingsRepository,
        notification_service: NotificationService | None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._account_repo = account_repo
        self._task_repo = task_repo
        self._platform_settings_repo = platform_settings_repo
        self._notifier = CleaningNotifier(notification_service, partner_repo)

    def run_all(self, *, today: date, now_hour: int) -> int:
        """Versendet fällige Erinnerungen für alle aktiven Mandanten."""
        target = today + timedelta(days=1)
        sent = 0
        for account in self._account_repo.list_by_status("active"):
            settings = self._platform_settings_repo.get(account.id)
            if settings is None or not settings.feature_enabled(
                FEATURE_CLEANING_SCHEDULE
            ):
                continue
            if in_quiet_window(
                now_hour,
                settings.cleaning_quiet_hours_start,
                settings.cleaning_quiet_hours_end,
            ):
                continue  # Sendefenster zu — nächster Zyklus holt es nach.
            sent += self._remind_account(account.id, target)
        return sent

    def _remind_account(self, account_id: str, target: date) -> int:
        tasks = [
            t
            for t in self._task_repo.list_tasks(
                account_id=account_id, date_from=target, date_to=target
            )
            if t.status in _OPEN_STATUSES
        ]
        count = 0
        for task in tasks:
            partners = self._notifier.partners_for(task.property_name, account_id)
            if not partners:
                continue
            correlation_id = f"cleaning_reminder:{task.task_id}:{task.cleaning_date}"
            self._notifier.notify(
                task,
                _extraction_from_task(task),
                partners,
                NotificationKind.CLEANING_REMINDER,
                account_id,
                correlation_id=correlation_id,
            )
            task.status_history.append(
                CleaningStatusEvent(
                    status=task.status, source="reminder", note="reminder_sent"
                )
            )
            self._task_repo.upsert(task, account_id=account_id)
            count += 1
        return count


def build_cleaning_reminder_service(ctx: AppContext) -> CleaningReminderService | None:
    """Baut den Reminder-Service aus dem AppContext (None, falls nicht verdrahtet)."""
    if ctx.cleaning_task_repo is None or ctx.cleaning_partner_repo is None:
        return None
    return CleaningReminderService(
        ctx.account_repo,
        ctx.cleaning_task_repo,
        ctx.cleaning_partner_repo,
        ctx.platform_settings_repo,
        ctx.notification_service,
    )

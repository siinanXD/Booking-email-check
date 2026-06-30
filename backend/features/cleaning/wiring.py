"""Verdrahtung der Putzplan-Komponenten (hält die Factory schlank)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.features.cleaning.service import CleaningScheduleService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)

if TYPE_CHECKING:
    from backend.features.notifications.notification_service import NotificationService
    from backend.infrastructure.repositories.mongo import Db
    from backend.infrastructure.repositories.platform_settings_repository import (
        PlatformSettingsRepository,
    )


def build_cleaning_service(
    db: Db,
    platform_settings_repo: PlatformSettingsRepository,
    notifier: NotificationService | None = None,
) -> tuple[CleaningPartnerRepository, CleaningTaskRepository, CleaningScheduleService]:
    """Erzeugt Putzpartner-/Auftrag-Repos und den Putzplan-Service."""
    partner_repo = CleaningPartnerRepository(db)
    task_repo = CleaningTaskRepository(db)
    service = CleaningScheduleService(
        partner_repo,
        task_repo,
        platform_settings_repo,
        notifier,
    )
    return partner_repo, task_repo, service

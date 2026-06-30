"""Tests für den Putzplan-Backfill aus bestehenden Extraktionen."""

from __future__ import annotations

from datetime import date

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.features.cleaning.backfill import backfill_account
from backend.features.cleaning.service import CleaningScheduleService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)

ACCOUNT = "acc-1"
TODAY = date(2026, 6, 30)


@pytest.fixture
def settings_repo(mock_db: Db) -> PlatformSettingsRepository:
    """Execute the operation."""
    return PlatformSettingsRepository(mock_db)


@pytest.fixture
def service(
    mock_db: Db, settings_repo: PlatformSettingsRepository
) -> CleaningScheduleService:
    """Execute the operation."""
    return CleaningScheduleService(
        CleaningPartnerRepository(mock_db),
        CleaningTaskRepository(mock_db),
        settings_repo,
    )


def _save(repo: ExtractionRepository, cid: str, **kw: object) -> None:
    repo.save(
        cid,
        f"msg-{cid}",
        BookingExtraction(**kw),  # type: ignore[arg-type]
        account_id=ACCOUNT,
    )


def test_backfill_creates_tasks_for_future_bookings(
    mock_db: Db,
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    extraction_repo: ExtractionRepository,
) -> None:
    """Nur zukünftige Neubuchungen/Änderungen werden übernommen."""
    settings_repo.save(
        PlatformSettingsRecord(id=ACCOUNT, features={FEATURE_CLEANING_SCHEDULE: True})
    )
    _save(
        extraction_repo,
        "future-1",
        intent=BookingIntent.NEW_BOOKING,
        booking_number="BN-1",
        property_name="Loft A",
        check_out=date(2026, 7, 10),
    )
    _save(
        extraction_repo,
        "past-1",
        intent=BookingIntent.NEW_BOOKING,
        booking_number="BN-2",
        property_name="Loft B",
        check_out=date(2026, 1, 5),
    )
    _save(
        extraction_repo,
        "cancel-1",
        intent=BookingIntent.CANCELLATION,
        booking_number="BN-3",
        property_name="Loft C",
        check_out=date(2026, 8, 1),
    )

    created = backfill_account(
        service, ACCOUNT, today=TODAY, extraction_repo=extraction_repo
    )
    assert created == 1
    tasks = CleaningTaskRepository(mock_db).list_tasks(account_id=ACCOUNT)
    assert len(tasks) == 1
    assert tasks[0].booking_number == "BN-1"


def test_backfill_noop_when_feature_disabled(
    service: CleaningScheduleService,
    extraction_repo: ExtractionRepository,
) -> None:
    """Ohne Freischaltung passiert nichts."""
    _save(
        extraction_repo,
        "future-1",
        intent=BookingIntent.NEW_BOOKING,
        booking_number="BN-1",
        property_name="Loft A",
        check_out=date(2026, 7, 10),
    )
    assert (
        backfill_account(service, ACCOUNT, today=TODAY, extraction_repo=extraction_repo)
        == 0
    )

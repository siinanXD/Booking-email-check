"""Tests für den Putzplan-Service (Auftrags-Lebenszyklus)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.features.cleaning.models import CleaningPartner, CleaningTaskStatus
from backend.features.cleaning.service import CleaningScheduleService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)

ACCOUNT = "acc-1"


@pytest.fixture
def settings_repo(mock_db: Db) -> PlatformSettingsRepository:
    """Execute the operation."""
    return PlatformSettingsRepository(mock_db)


@pytest.fixture
def partner_repo(mock_db: Db) -> CleaningPartnerRepository:
    """Execute the operation."""
    return CleaningPartnerRepository(mock_db)


@pytest.fixture
def task_repo(mock_db: Db) -> CleaningTaskRepository:
    """Execute the operation."""
    return CleaningTaskRepository(mock_db)


@pytest.fixture
def service(
    partner_repo: CleaningPartnerRepository,
    task_repo: CleaningTaskRepository,
    settings_repo: PlatformSettingsRepository,
) -> CleaningScheduleService:
    """Execute the operation."""
    return CleaningScheduleService(partner_repo, task_repo, settings_repo)


def _enable(repo: PlatformSettingsRepository, *, offset: int = 0) -> None:
    repo.save(
        PlatformSettingsRecord(
            id=ACCOUNT,
            features={FEATURE_CLEANING_SCHEDULE: True},
            cleaning_checkout_offset_days=offset,
        )
    )


def _booking(
    intent: BookingIntent = BookingIntent.NEW_BOOKING,
    *,
    booking_number: str = "BN-100",
    check_out: date = date(2026, 7, 10),
    property_name: str = "Loft A",
) -> BookingExtraction:
    return BookingExtraction(
        intent=intent,
        guest_name="Max Muster",
        booking_number=booking_number,
        property_name=property_name,
        check_in=date(2026, 7, 5),
        check_out=check_out,
    )


def _partner(repo: CleaningPartnerRepository, property_name: str = "Loft A") -> None:
    repo.upsert(
        CleaningPartner(
            partner_id="p-1",
            account_id=ACCOUNT,
            name="CleanCo",
            phone="+4917000000",
            property_names=[property_name],
        ),
        account_id=ACCOUNT,
    )


def test_disabled_feature_is_noop(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Ohne Freischaltung wird kein Auftrag erzeugt."""
    result = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert result is None
    assert task_repo.list_tasks(account_id=ACCOUNT) == []


def test_new_booking_with_partner_scheduled(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
) -> None:
    """Neubuchung mit Putzpartner → SCHEDULED, Termin = Check-out."""
    _enable(settings_repo)
    _partner(partner_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.status == CleaningTaskStatus.SCHEDULED
    assert task.partner_id == "p-1"
    assert task.cleaning_date == date(2026, 7, 10)


def test_new_booking_without_partner_unassigned(
    service: CleaningScheduleService, settings_repo: PlatformSettingsRepository
) -> None:
    """Neubuchung ohne Putzpartner → UNASSIGNED, fällt nicht durch."""
    _enable(settings_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.status == CleaningTaskStatus.UNASSIGNED
    assert task.partner_id is None


def test_offset_shifts_cleaning_date(
    service: CleaningScheduleService, settings_repo: PlatformSettingsRepository
) -> None:
    """Offset verschiebt den Putztermin nach hinten."""
    _enable(settings_repo, offset=1)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.cleaning_date == date(2026, 7, 11)


def test_reingestion_is_idempotent(
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    task_repo: CleaningTaskRepository,
) -> None:
    """Mehrfach eintreffende Buchungsmail erzeugt keinen Doppelauftrag."""
    _enable(settings_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    service.process_booking_event("c2", _booking(), account_id=ACCOUNT)
    assert len(task_repo.list_tasks(account_id=ACCOUNT)) == 1


def test_cancellation_cancels_existing(
    service: CleaningScheduleService, settings_repo: PlatformSettingsRepository
) -> None:
    """Stornierung verknüpft über booking_number und setzt CANCELLED."""
    _enable(settings_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    cancelled = service.process_booking_event(
        "c2", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    assert cancelled is not None
    assert cancelled.status == CleaningTaskStatus.CANCELLED
    assert cancelled.cancelled_at is not None


def test_cancellation_without_existing_creates_stub(
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    task_repo: CleaningTaskRepository,
) -> None:
    """Storno vor Auftragsanlage (out-of-order) → CANCELLED-Stub."""
    _enable(settings_repo)
    task = service.process_booking_event(
        "c1", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    assert task is not None
    assert task.status == CleaningTaskStatus.CANCELLED
    assert len(task_repo.list_tasks(account_id=ACCOUNT)) == 1


def test_rebooking_after_cancel_reopens(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
) -> None:
    """Storniert → später erneut gebucht reaktiviert den Auftrag."""
    _enable(settings_repo)
    _partner(partner_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    service.process_booking_event(
        "c2", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    reopened = service.process_booking_event(
        "c3",
        _booking(),
        account_id=ACCOUNT,
        event_at=datetime.now(UTC) + timedelta(hours=1),
    )
    assert reopened is not None
    assert reopened.status == CleaningTaskStatus.SCHEDULED
    assert reopened.cancelled_at is None


def test_stale_event_does_not_reopen_cancelled(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
) -> None:
    """Eine erneut verarbeitete ältere Mail weckt den Storno nicht auf.

    Genau das passierte in Produktion: der Backfill spielte die Änderungsmail
    von vor dem Storno noch einmal ein, der Auftrag stand wieder auf
    ``scheduled`` und die Putzkraft wurde zu einem stornierten Zimmer geschickt.
    """
    _enable(settings_repo)
    _partner(partner_repo)
    stale = datetime.now(UTC) - timedelta(hours=1)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT, event_at=stale)
    service.process_booking_event(
        "c2", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )

    replayed = service.process_booking_event(
        "c1", _booking(), account_id=ACCOUNT, event_at=stale
    )
    assert replayed is not None
    assert replayed.status == CleaningTaskStatus.CANCELLED

    # Auch ohne Zeitstempel (Backfill) bleibt der Storno bestehen.
    backfilled = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert backfilled is not None
    assert backfilled.status == CleaningTaskStatus.CANCELLED


def test_manual_edit_not_clobbered_by_change(
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    task_repo: CleaningTaskRepository,
) -> None:
    """Eine CHANGE-Mail überschreibt manuell gesetzten Status nicht."""
    _enable(settings_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    task.manually_edited = True
    task.record_status(CleaningTaskStatus.DONE, source="manual")
    task_repo.upsert(task, account_id=ACCOUNT)

    changed = service.process_booking_event(
        "c2",
        _booking(BookingIntent.CHANGE, check_out=date(2026, 7, 12)),
        account_id=ACCOUNT,
    )
    assert changed is not None
    assert changed.status == CleaningTaskStatus.DONE
    assert changed.check_out == date(2026, 7, 12)
    assert changed.cleaning_date == date(2026, 7, 12)


def test_tenant_isolation(
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    task_repo: CleaningTaskRepository,
) -> None:
    """Aufträge sind mandantenscharf getrennt."""
    _enable(settings_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task_repo.list_tasks(account_id="other") == []


def test_overlap_detection_flags_same_room_overlapping_stays() -> None:
    """Gleiches Zimmer + überlappende Aufenthalte werden beide markiert."""
    from backend.features.cleaning.models import CleaningTask
    from backend.features.cleaning.overlap import overlapping_task_ids

    def _task(tid: str, room: str, ci: date, co: date) -> CleaningTask:
        return CleaningTask(
            task_id=tid,
            account_id=ACCOUNT,
            property_name="Loft A",
            room_number=room,
            check_in=ci,
            check_out=co,
        )

    a = _task("a", "3", date(2026, 7, 5), date(2026, 7, 10))
    b = _task("b", "3", date(2026, 7, 8), date(2026, 7, 12))  # überlappt a
    c = _task("c", "3", date(2026, 7, 12), date(2026, 7, 14))  # nahtlos an b → ok
    d = _task("d", "4", date(2026, 7, 6), date(2026, 7, 9))  # anderes Zimmer

    flagged = overlapping_task_ids([a, b, c, d])
    assert flagged == {"a", "b"}

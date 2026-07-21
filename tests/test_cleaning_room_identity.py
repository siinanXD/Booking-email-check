"""Zimmer in der Auftrags-Identität — eine Reservierung, zwei Zimmer.

Mehrzimmer-Reservierungen tragen *eine* Buchungsnummer. Ohne Zimmer im Seed
teilten sich beide Zimmer eine task_id, und der zweite Auftrag überschrieb den
ersten — geputzt wurde dann nur eines der Zimmer.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.features.cleaning.identity import cleaning_task_id, task_id_for
from backend.features.cleaning.migration import get_or_adopt, legacy_task_id
from backend.features.cleaning.models import CleaningPartner
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

ACCOUNT = "acc-room"


@pytest.fixture
def task_repo(mock_db: Db) -> CleaningTaskRepository:
    """Auftrags-Repository auf der In-Memory-DB."""
    return CleaningTaskRepository(mock_db)


@pytest.fixture
def service(mock_db: Db, task_repo: CleaningTaskRepository) -> CleaningScheduleService:
    """Freigeschalteter Putzplan-Service."""
    settings_repo = PlatformSettingsRepository(mock_db)
    settings_repo.save(
        PlatformSettingsRecord(
            id=ACCOUNT,
            features={FEATURE_CLEANING_SCHEDULE: True},
            cleaning_checkout_offset_days=0,
        )
    )
    partner_repo = CleaningPartnerRepository(mock_db)
    partner_repo.upsert(
        CleaningPartner(
            partner_id="p-1",
            account_id=ACCOUNT,
            name="CleanCo",
            phone="+4917000000",
            property_names=["Münzbach Ferienzimmer"],
        ),
        account_id=ACCOUNT,
    )
    return CleaningScheduleService(partner_repo, task_repo, settings_repo)


def _booking(room: str | None) -> BookingExtraction:
    """Dieselbe Reservierung, einmal je Zimmer — gleiche Buchungsnummer."""
    return BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        guest_name="Stefan Blass",
        booking_number="BN-500",
        property_name="Münzbach Ferienzimmer",
        room_number=room,
        check_in=date(2026, 7, 24),
        check_out=date(2026, 7, 26),
    )


def test_zimmer_trennt_die_task_id() -> None:
    """Gleiche Buchungsnummer, verschiedene Zimmer → verschiedene Aufträge."""
    assert task_id_for(_booking("3"), ACCOUNT) != task_id_for(_booking("4"), ACCOUNT)


def test_ohne_zimmer_bleibt_die_task_id_stabil() -> None:
    """Bestandsaufträge ohne Zimmerangabe behalten ihren bisherigen Schlüssel."""
    assert task_id_for(_booking(None), ACCOUNT) == cleaning_task_id(
        account_id=ACCOUNT,
        booking_number="BN-500",
        property_name="Münzbach Ferienzimmer",
        check_out=date(2026, 7, 26),
        guest_name="Stefan Blass",
    )


def test_beide_zimmer_landen_im_putzplan(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Der Kundenfall: Zimmer 3 und 4, früher blieb nur Zimmer 4 übrig."""
    service.process_booking_event("c-3", _booking("3"), account_id=ACCOUNT)
    service.process_booking_event("c-4", _booking("4"), account_id=ACCOUNT)

    tasks = task_repo.list_tasks(account_id=ACCOUNT)
    assert len(tasks) == 2
    assert {t.room_number for t in tasks} == {"3", "4"}


def test_erneute_mail_dupliziert_nicht(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Idempotenz bleibt erhalten — dieselbe Mail erzeugt keinen zweiten Auftrag."""
    service.process_booking_event("c-3", _booking("3"), account_id=ACCOUNT)
    service.process_booking_event("c-3", _booking("3"), account_id=ACCOUNT)
    assert len(task_repo.list_tasks(account_id=ACCOUNT)) == 1


def test_altauftrag_wird_uebernommen_statt_verdoppelt(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Bestand unter altem Schlüssel wandert mit, statt daneben neu zu entstehen."""
    booking = _booking("4")
    # Auftrag anlegen und künstlich auf den alten Schlüssel zurücksetzen.
    service.process_booking_event("c-4", booking, account_id=ACCOUNT)
    [task] = task_repo.list_tasks(account_id=ACCOUNT)
    task_repo.delete(task.task_id, account_id=ACCOUNT)
    task.task_id = legacy_task_id(booking, ACCOUNT)
    task.note = "manuell ergaenzt"
    task_repo.upsert(task, account_id=ACCOUNT)

    service.process_booking_event("c-4", booking, account_id=ACCOUNT)

    tasks = task_repo.list_tasks(account_id=ACCOUNT)
    assert len(tasks) == 1
    assert tasks[0].task_id == task_id_for(booking, ACCOUNT)
    assert tasks[0].note == "manuell ergaenzt"  # manuelle Edits überleben


def test_schwesterzimmer_wird_nicht_uebernommen(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Ein Altauftrag für Zimmer 4 darf nicht zu Zimmer 3 umgewidmet werden."""
    service.process_booking_event("c-4", _booking("4"), account_id=ACCOUNT)
    [task] = task_repo.list_tasks(account_id=ACCOUNT)
    task_repo.delete(task.task_id, account_id=ACCOUNT)
    task.task_id = legacy_task_id(_booking("4"), ACCOUNT)
    task_repo.upsert(task, account_id=ACCOUNT)

    adopted = get_or_adopt(
        task_repo, _booking("3"), ACCOUNT, task_id_for(_booking("3"), ACCOUNT)
    )
    assert adopted is None

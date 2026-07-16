"""Stammdaten eines Putzauftrags folgen der Mail — auch bei Folgemails.

Regression: `_update_existing` schrieb nur Termine, Status und Partner. Zimmer,
Objekt und Gast blieben auf dem Stand der ersten Mail. Ein einmal falsch
angelegter Auftrag war damit für immer falsch — im Bestand standen acht Aufträge
mit room_number=None, obwohl "Zimmer Nr. 3" wörtlich in der Mail stand. Der
Zimmer-Fix vom 3. Juli erreichte die Altdaten nie.

Abgegrenzt: `manually_edited` schützt Status, Partner und Bemerkung. Stammdaten
sind über die API nicht editierbar und dürfen deshalb immer nachziehen.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.features.billing.plans import FEATURE_CLEANING_SCHEDULE
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
    PlatformSettingsRepository,
)

ACCOUNT = "acc-1"
PROPERTY = "Münzbach Ferienzimmer"


class FakeEntitlements:
    def effective_features(self, account_id: str) -> set[str]:
        return {FEATURE_CLEANING_SCHEDULE}


class FakeNotifications:
    def dispatch_to_partner(self, *a: Any, **kw: Any) -> Any:
        from backend.core.models.notification import NotificationStatus

        class _Rec:
            status = NotificationStatus.SENT
            error = None

        return _Rec()


@pytest.fixture
def task_repo(mock_db: Db) -> CleaningTaskRepository:
    return CleaningTaskRepository(mock_db)


@pytest.fixture
def service(mock_db: Db, task_repo: CleaningTaskRepository) -> CleaningScheduleService:
    partner_repo = CleaningPartnerRepository(mock_db)
    partner_repo.upsert(
        CleaningPartner(
            partner_id="p1",
            name="Dennis",
            phone="+4915711111111",
            property_names=[PROPERTY],
        ),
        account_id=ACCOUNT,
    )
    return CleaningScheduleService(
        partner_repo,
        task_repo,
        PlatformSettingsRepository(mock_db),
        FakeNotifications(),  # type: ignore[arg-type]
        FakeEntitlements(),  # type: ignore[arg-type]
    )


def _extraction(**kw: Any) -> BookingExtraction:
    base: dict[str, Any] = {
        "guest_name": "Coosemans",
        "property_name": PROPERTY,
        "check_in": "2026-07-17",
        "check_out": "2026-07-18",
        "booking_number": "89790382",
        "intent": BookingIntent.NEW_BOOKING,
    }
    base.update(kw)
    return BookingExtraction(**base)


def test_zimmer_wird_von_folgemail_nachgezogen(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Der Kernfehler: Auftrag ohne Zimmer blieb ohne Zimmer."""
    service.process_booking_event(
        "corr-1", _extraction(room_number=None), account_id=ACCOUNT, notify=False
    )

    service.process_booking_event(
        "corr-2", _extraction(room_number="3"), account_id=ACCOUNT, notify=False
    )

    tasks = task_repo.list_tasks(account_id=ACCOUNT)
    assert [t.room_number for t in tasks] == ["3"]


def test_objekt_und_gast_werden_nachgezogen(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    service.process_booking_event(
        "corr-1",
        _extraction(property_name="Münzbach Ferienzimmer Zimmer Nr. 3"),
        account_id=ACCOUNT,
        notify=False,
    )

    service.process_booking_event(
        "corr-2",
        _extraction(property_name=PROPERTY, room_number="3", guest_name="Coosemans An"),
        account_id=ACCOUNT,
        notify=False,
    )

    task = task_repo.list_tasks(account_id=ACCOUNT)[0]
    assert task.property_name == PROPERTY
    assert task.room_number == "3"
    assert task.guest_name == "Coosemans An"


def test_leere_felder_loeschen_nichts(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Eine dürftige Folgemail darf gute Daten nicht ausradieren."""
    service.process_booking_event(
        "corr-1", _extraction(room_number="3"), account_id=ACCOUNT, notify=False
    )

    service.process_booking_event(
        "corr-2",
        _extraction(room_number=None, guest_name=None),
        account_id=ACCOUNT,
        notify=False,
    )

    task = task_repo.list_tasks(account_id=ACCOUNT)[0]
    assert task.room_number == "3"
    assert task.guest_name == "Coosemans"


def test_manuelle_edits_bleiben_trotz_stammdaten_update(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """`manually_edited` schützt Status/Bemerkung — nicht die Stammdaten."""
    service.process_booking_event(
        "corr-1", _extraction(room_number=None), account_id=ACCOUNT, notify=False
    )
    task = task_repo.list_tasks(account_id=ACCOUNT)[0]
    task.manually_edited = True
    task.note = "Schlüssel beim Nachbarn"
    task.record_status(CleaningTaskStatus.DONE, source="manual")
    task_repo.upsert(task, account_id=ACCOUNT)

    service.process_booking_event(
        "corr-2", _extraction(room_number="3"), account_id=ACCOUNT, notify=False
    )

    updated = task_repo.list_tasks(account_id=ACCOUNT)[0]
    assert updated.room_number == "3"
    assert updated.note == "Schlüssel beim Nachbarn"
    assert updated.status == CleaningTaskStatus.DONE

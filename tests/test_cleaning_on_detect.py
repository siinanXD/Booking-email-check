"""Putzauftrag entsteht beim Erkennen, Versand erst bei Freigabe.

Regression: Aufträge wurden erst in finalize() bei status="approved" angelegt.
Wer Entwürfe nicht abarbeitete, hatte einen eingefrorenen Putzplan — die
Buchung stand in der Liste, die Reinigung fehlte.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.workflows.nodes.cleaning_hook import schedule_cleaning_on_detect
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
    """Zeichnet Partner-Versand auf, statt WhatsApp zu schicken."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    def dispatch_to_partner(
        self,
        correlation_id: str,
        extraction: BookingExtraction,
        *,
        kind: Any,
        recipient_e164: str,
        locale: str,
        account_id: str | None = None,
    ) -> Any:
        from backend.core.models.notification import NotificationStatus

        self.sent.append(recipient_e164)

        class _Rec:
            status = NotificationStatus.SENT
            error = None

        return _Rec()


class FakeEmail:
    correlation_id = "corr-1"
    account_id = ACCOUNT
    received_at = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def notifications() -> FakeNotifications:
    return FakeNotifications()


@pytest.fixture
def task_repo(mock_db: Db) -> CleaningTaskRepository:
    return CleaningTaskRepository(mock_db)


@pytest.fixture
def service(
    mock_db: Db, notifications: FakeNotifications, task_repo: CleaningTaskRepository
) -> CleaningScheduleService:
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
        notifications,  # type: ignore[arg-type]
        FakeEntitlements(),  # type: ignore[arg-type]
    )


def _extraction() -> BookingExtraction:
    return BookingExtraction(
        guest_name="Coosemans",
        property_name=PROPERTY,
        check_in="2026-07-17",
        check_out="2026-07-18",
        booking_number="89790382",
        intent=BookingIntent.NEW_BOOKING,
    )


def test_auftrag_entsteht_ohne_freigabe(
    service: CleaningScheduleService,
    task_repo: CleaningTaskRepository,
    notifications: FakeNotifications,
) -> None:
    """Der Kern: Erkennen reicht, Review nicht nötig."""
    schedule_cleaning_on_detect(service, FakeEmail(), _extraction())  # type: ignore[arg-type]

    tasks = task_repo.list_tasks(account_id=ACCOUNT)
    assert len(tasks) == 1
    assert tasks[0].cleaning_date is not None
    assert tasks[0].cleaning_date.isoformat() == "2026-07-18"
    # Kein Versand ohne menschliche Entscheidung.
    assert notifications.sent == []
    assert tasks[0].status == CleaningTaskStatus.SCHEDULED


def test_freigabe_holt_versand_genau_einmal_nach(
    service: CleaningScheduleService,
    task_repo: CleaningTaskRepository,
    notifications: FakeNotifications,
) -> None:
    schedule_cleaning_on_detect(service, FakeEmail(), _extraction())  # type: ignore[arg-type]
    assert notifications.sent == []

    # finalize() bei Freigabe
    service.process_booking_event("corr-1", _extraction(), account_id=ACCOUNT)
    assert notifications.sent == ["+4915711111111"]

    # Zweite Freigabe (Re-Run, Retry) darf nicht erneut senden.
    service.process_booking_event("corr-1", _extraction(), account_id=ACCOUNT)
    assert notifications.sent == ["+4915711111111"]
    assert len(task_repo.list_tasks(account_id=ACCOUNT)) == 1


def test_detect_ist_idempotent(
    service: CleaningScheduleService, task_repo: CleaningTaskRepository
) -> None:
    """Mehrfach-Ingest derselben Mail darf keine Duplikate erzeugen."""
    for _ in range(3):
        schedule_cleaning_on_detect(service, FakeEmail(), _extraction())  # type: ignore[arg-type]
    assert len(task_repo.list_tasks(account_id=ACCOUNT)) == 1


def test_ohne_service_kein_fehler() -> None:
    """Der Hook darf den Mail-Workflow nie unterbrechen."""
    schedule_cleaning_on_detect(None, FakeEmail(), _extraction())  # type: ignore[arg-type]


def test_fehler_im_putzplan_bricht_workflow_nicht(
    service: CleaningScheduleService,
) -> None:
    class Boom:
        def process_booking_event(self, *a: Any, **k: Any) -> None:
            raise RuntimeError("boom")

    schedule_cleaning_on_detect(Boom(), FakeEmail(), _extraction())  # type: ignore[arg-type]

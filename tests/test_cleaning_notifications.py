"""Tests für WhatsApp-Versand des Putzplans (Phase 2)."""

from __future__ import annotations

from datetime import date

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.settings import Settings
from backend.features.cleaning.models import CleaningPartner, CleaningTaskStatus
from backend.features.cleaning.service import CleaningScheduleService
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.mocks import MockWhatsAppClient

ACCOUNT = "acc-1"


def _env_settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "test",
            "MONGODB_URI": "mongodb://localhost:27017",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
        }
    )


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
def client() -> MockWhatsAppClient:
    """Execute the operation."""
    return MockWhatsAppClient()


@pytest.fixture
def service(
    mock_db: Db,
    partner_repo: CleaningPartnerRepository,
    task_repo: CleaningTaskRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> CleaningScheduleService:
    """Cleaning-Service mit echtem NotificationService + Mock-Client."""
    notifier = NotificationService(
        _env_settings(),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        PropertyRecipientRepository(mock_db),
        settings_repo,
        whatsapp_client=client,
    )
    return CleaningScheduleService(partner_repo, task_repo, settings_repo, notifier)


def _enable(repo: PlatformSettingsRepository, *, whatsapp: bool = True) -> None:
    repo.save(
        PlatformSettingsRecord(
            id=ACCOUNT,
            features={FEATURE_CLEANING_SCHEDULE: True},
            whatsapp_enabled=whatsapp,
        )
    )


def _partner(repo: CleaningPartnerRepository) -> None:
    repo.upsert(
        CleaningPartner(
            partner_id="p-1",
            account_id=ACCOUNT,
            name="CleanCo",
            phone="+491700000000",
            locale="de",
            property_names=["Loft A"],
        ),
        account_id=ACCOUNT,
    )


def _partner2(repo: CleaningPartnerRepository) -> None:
    repo.upsert(
        CleaningPartner(
            partner_id="p-2",
            account_id=ACCOUNT,
            name="CleanCo 2",
            phone="+491700000002",
            locale="de",
            property_names=["Loft A"],
        ),
        account_id=ACCOUNT,
    )


def _booking(
    intent: BookingIntent = BookingIntent.NEW_BOOKING,
    *,
    check_out: date = date(2026, 7, 10),
) -> BookingExtraction:
    return BookingExtraction(
        intent=intent,
        guest_name="Max Muster",
        booking_number="BN-100",
        property_name="Loft A",
        check_in=date(2026, 7, 5),
        check_out=check_out,
    )


def test_new_booking_notifies_partner_and_marks_notified(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Neubuchung mit Partner + WhatsApp an → Status NOTIFIED."""
    _enable(settings_repo)
    _partner(partner_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.status == CleaningTaskStatus.NOTIFIED
    assert task.last_notification_status == "sent"
    assert client.sent[0].template_name == "booking_cleaning_task_de"
    assert client.sent[0].recipient_e164 == "+491700000000"


def test_cancellation_notifies_partner_with_cancelled_template(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Storno → eigene 'Auftrag entfällt'-WhatsApp an den Partner."""
    _enable(settings_repo)
    _partner(partner_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    cancelled = service.process_booking_event(
        "c2", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    assert cancelled is not None
    assert cancelled.status == CleaningTaskStatus.CANCELLED
    last = client.sent[-1]
    assert last.template_name == "booking_cleaning_cancelled_de"
    assert last.template_params[0].startswith("Loft A")
    assert last.template_params[3] == "Max Muster"


def test_cancellation_without_partner_sends_nothing(
    service: CleaningScheduleService,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Ohne zugeordneten Partner kein Versand, aber Auftrag storniert."""
    _enable(settings_repo)
    task = service.process_booking_event(
        "c1", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    assert task is not None
    assert task.status == CleaningTaskStatus.CANCELLED
    assert client.sent == []


def test_new_booking_fans_out_to_all_partners(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Neubuchung benachrichtigt alle aktiven Partner der Wohnung."""
    _enable(settings_repo)
    _partner(partner_repo)
    _partner2(partner_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.status == CleaningTaskStatus.NOTIFIED
    assert {m.recipient_e164 for m in client.sent} == {
        "+491700000000",
        "+491700000002",
    }


def test_change_with_new_date_renotifies(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Verschobener Putztermin (CHANGE) informiert den Partner erneut."""
    _enable(settings_repo)
    _partner(partner_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    changed = service.process_booking_event(
        "c2",
        _booking(BookingIntent.CHANGE, check_out=date(2026, 7, 12)),
        account_id=ACCOUNT,
    )
    assert changed is not None
    assert changed.status == CleaningTaskStatus.NOTIFIED
    assert changed.cleaning_date == date(2026, 7, 12)
    assert len(client.sent) == 2  # Neubuchung + Re-Notify


def test_cancellation_fans_out_to_all_partners(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Storno geht an alle aktiven Partner der Wohnung."""
    _enable(settings_repo)
    _partner(partner_repo)
    _partner2(partner_repo)
    service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    client.sent.clear()
    service.process_booking_event(
        "c2", _booking(BookingIntent.CANCELLATION), account_id=ACCOUNT
    )
    assert {m.template_name for m in client.sent} == {"booking_cleaning_cancelled_de"}
    assert len(client.sent) == 2


def test_disabled_whatsapp_keeps_scheduled(
    service: CleaningScheduleService,
    partner_repo: CleaningPartnerRepository,
    settings_repo: PlatformSettingsRepository,
    client: MockWhatsAppClient,
) -> None:
    """Feature an, WhatsApp aus → Auftrag bleibt SCHEDULED, kein Versand."""
    _enable(settings_repo, whatsapp=False)
    _partner(partner_repo)
    task = service.process_booking_event("c1", _booking(), account_id=ACCOUNT)
    assert task is not None
    assert task.status == CleaningTaskStatus.SCHEDULED
    assert client.sent == []

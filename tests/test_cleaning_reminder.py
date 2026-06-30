"""Tests für die Putz-Erinnerungen (Vortag, Multi-Partner, Quiet-Hours)."""

from __future__ import annotations

from datetime import date

import pytest

from backend.core.config.settings import Settings
from backend.features.cleaning.models import (
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.cleaning.notifier import in_quiet_window
from backend.features.cleaning.reminder_service import CleaningReminderService
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.repositories.account_repository import AccountRepository
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

TODAY = date(2026, 7, 1)
TOMORROW = date(2026, 7, 2)


def _env_settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "test",
            "MONGODB_URI": "mongodb://localhost:27017",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
        }
    )


def _setup(mock_db: Db, client: MockWhatsAppClient, *, quiet=(0, 0)):
    account_repo = AccountRepository(mock_db)
    account = account_repo.create(
        display_name="T",
        contact_email="t@test.local",
        account_type="business",
        company_name="T",
        status="active",
    )
    settings_repo = PlatformSettingsRepository(mock_db)
    settings_repo.save(
        PlatformSettingsRecord(
            id=account.id,
            features={FEATURE_CLEANING_SCHEDULE: True},
            whatsapp_enabled=True,
            cleaning_quiet_hours_start=quiet[0],
            cleaning_quiet_hours_end=quiet[1],
        )
    )
    partner_repo = CleaningPartnerRepository(mock_db)
    for pid, phone in (("p-1", "+491700000001"), ("p-2", "+491700000002")):
        partner_repo.upsert(
            CleaningPartner(
                partner_id=pid,
                account_id=account.id,
                name=pid,
                phone=phone,
                property_names=["Loft A"],
            ),
            account_id=account.id,
        )
    task_repo = CleaningTaskRepository(mock_db)
    task = CleaningTask(
        task_id="t-1",
        account_id=account.id,
        property_name="Loft A",
        check_out=TOMORROW,
        cleaning_date=TOMORROW,
        status=CleaningTaskStatus.SCHEDULED,
    )
    task_repo.upsert(task, account_id=account.id)
    notifier = NotificationService(
        _env_settings(),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        PropertyRecipientRepository(mock_db),
        settings_repo,
        whatsapp_client=client,
    )
    service = CleaningReminderService(
        account_repo, task_repo, partner_repo, settings_repo, notifier
    )
    return service


def test_in_quiet_window_wraps_midnight() -> None:
    """22–7 schließt 23 und 3 ein, nicht 12."""
    assert in_quiet_window(23, 22, 7)
    assert in_quiet_window(3, 22, 7)
    assert not in_quiet_window(12, 22, 7)
    assert not in_quiet_window(12, 0, 0)  # deaktiviert


def test_reminder_fans_out_to_all_partners(
    mock_db: Db, client: MockWhatsAppClient
) -> None:
    """Erinnerung am Vortag geht an alle aktiven Partner der Wohnung."""
    service = _setup(mock_db, client)
    sent = service.run_all(today=TODAY, now_hour=12)
    assert sent == 1
    assert len(client.sent) == 2
    assert client.sent[0].template_name == "booking_cleaning_reminder_de"


def test_reminder_is_idempotent(mock_db: Db, client: MockWhatsAppClient) -> None:
    """Zweiter Lauf am selben Tag sendet nicht erneut."""
    service = _setup(mock_db, client)
    service.run_all(today=TODAY, now_hour=12)
    service.run_all(today=TODAY, now_hour=13)
    assert len(client.sent) == 2  # keine Duplikate


def test_reminder_skips_during_quiet_hours(
    mock_db: Db, client: MockWhatsAppClient
) -> None:
    """Im Sendefenster-Verbot wird nichts verschickt."""
    service = _setup(mock_db, client, quiet=(8, 18))
    service.run_all(today=TODAY, now_hour=12)
    assert client.sent == []


@pytest.fixture
def client() -> MockWhatsAppClient:
    """Execute the operation."""
    return MockWhatsAppClient()

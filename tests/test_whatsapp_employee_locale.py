"""WhatsApp-Sprachen für Mitarbeiter-Empfänger."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.settings import Settings
from backend.core.models.notification import NotificationKind, NotificationStatus
from backend.features.notifications.notification_service import NotificationService
from backend.features.notifications.whatsapp_locale import (
    localized_template_name,
    template_name_for_kind,
)
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
    PropertyWhatsAppEmployee,
)
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.mocks import MockWhatsAppClient


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "OPENAI_API_KEY": "test",
        "MONGODB_URI": "mongodb://localhost:27017",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "WHATSAPP_ENABLED": True,
        "WHATSAPP_DEFAULT_RECIPIENTS": "+491701234567",
        "WHATSAPP_TEMPLATE_LANGUAGE": "de",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_localized_template_name_derives_from_de_base() -> None:
    assert localized_template_name("booking_cleaning_task_de", "en") == (
        "booking_cleaning_task_en"
    )
    assert localized_template_name("booking_cleaning_task_de", "pl") == (
        "booking_cleaning_task_pl"
    )
    assert localized_template_name("booking_cleaning_task_de", "de") == (
        "booking_cleaning_task_de"
    )


def test_template_name_for_kind_uses_locale_only_for_cleaning() -> None:
    settings = _settings()
    assert (
        template_name_for_kind(
            NotificationKind.BOOKING_CLEANING_TASK,
            settings,
            "it",
        )
        == "booking_cleaning_task_it"
    )
    assert (
        template_name_for_kind(
            NotificationKind.BOOKING_STATUS_NOTICE,
            settings,
            "pl",
        )
        == "booking_status_notice_de"
    )
    assert (
        template_name_for_kind(
            NotificationKind.BOOKING_GUEST_INQUIRY,
            settings,
            "es",
        )
        == "booking_guest_inquiry_de"
    )


def test_employee_receives_localized_template(mock_db) -> None:
    client = MockWhatsAppClient()
    property_repo = PropertyRecipientRepository(mock_db)
    account_id = "test-account"
    property_repo.upsert(
        account_id,
        "Apartment Mitte",
        [
            PropertyWhatsAppEmployee(
                phone_e164="+491709999999",
                locale="pl",
            )
        ],
    )
    svc = NotificationService(
        _settings(WHATSAPP_DEFAULT_RECIPIENTS=""),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        property_repo,
        PlatformSettingsRepository(mock_db),
        whatsapp_client=client,
    )
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Apartment Mitte",
        booking_number="AB200",
        check_in=date(2026, 6, 10),
        check_out=date(2026, 6, 15),
    )
    records = svc.dispatch_after_approval(
        "corr-locale", extraction, account_id=account_id
    )
    assert len(records) == 1
    assert records[0].status == NotificationStatus.SENT
    assert client.sent[0].recipient_e164 == "+491709999999"
    assert client.sent[0].template_name == "booking_cleaning_task_pl"
    assert client.sent[0].template_language == "pl"
    assert client.sent[0].template_params[3] == "Sprzątanie po wymeldowaniu"


def test_host_keeps_account_language_when_employee_also_present(mock_db) -> None:
    client = MockWhatsAppClient()
    property_repo = PropertyRecipientRepository(mock_db)
    account_id = "test-account"
    property_repo.upsert(
        account_id,
        "Apartment Mitte",
        [PropertyWhatsAppEmployee(phone_e164="+491709999999", locale="es")],
    )
    svc = NotificationService(
        _settings(),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        property_repo,
        PlatformSettingsRepository(mock_db),
        whatsapp_client=client,
    )
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Apartment Mitte",
        booking_number="AB201",
    )
    records = svc.dispatch_after_approval(
        "corr-host-locale", extraction, account_id=account_id
    )
    assert len(records) == 2
    host_msg = next(m for m in client.sent if m.recipient_e164 == "+491701234567")
    employee_msg = next(m for m in client.sent if m.recipient_e164 == "+491709999999")
    assert host_msg.template_language == "de"
    assert host_msg.template_name == "booking_status_notice_de"
    assert host_msg.template_params[0] == "Neue Buchung"
    assert employee_msg.template_language == "es"
    assert employee_msg.template_name == "booking_cleaning_task_es"


def test_legacy_phones_default_to_german(mock_db) -> None:
    property_repo = PropertyRecipientRepository(mock_db)
    account_id = "legacy-account"
    property_repo.upsert(account_id, "Haus A", ["+491708888888"])
    employees = property_repo.get_employees("Haus A", account_id=account_id)
    assert len(employees) == 1
    assert employees[0].locale == "de"

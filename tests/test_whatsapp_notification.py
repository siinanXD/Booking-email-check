"""WhatsApp-Notification-Scaffold (deaktiviert by default)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.settings import Settings
from backend.core.models.notification import NotificationKind, NotificationStatus
from backend.features.notifications.notification_service import NotificationService
from backend.features.notifications.whatsapp_client import (
    DisabledWhatsAppClient,
    WhatsAppClient,
)
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
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
    }
    base.update(overrides)
    return Settings.model_validate(base)


def _notification_svc(
    mock_db: object,
    client: WhatsAppClient | None = None,
    **settings_overrides: object,
) -> NotificationService:
    platform_repo = PlatformSettingsRepository(mock_db)
    return NotificationService(
        _settings(**settings_overrides),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        PropertyRecipientRepository(mock_db),
        platform_repo,
        whatsapp_client=client,
    )


def test_dispatch_disabled_returns_empty(mock_db) -> None:
    """WHATSAPP_ENABLED=false: kein Outbox-Eintrag."""
    svc = _notification_svc(mock_db, WHATSAPP_ENABLED=False)
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Apartment Mitte",
        booking_number="AB100",
        check_in=date(2026, 6, 10),
        check_out=date(2026, 6, 15),
    )
    assert svc.dispatch_after_approval("corr-1", extraction) == []


def test_dispatch_new_booking_host_gets_status_notice(mock_db) -> None:
    """Neue Buchung → Host erhält Status-Template „Neue Buchung“."""
    client = MockWhatsAppClient()
    svc = _notification_svc(mock_db, client)
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Apartment Mitte",
        booking_number="AB100",
        guest_name="Max Mustermann",
        check_in=date(2026, 6, 10),
        check_out=date(2026, 6, 15),
    )
    records = svc.dispatch_after_approval("corr-2", extraction)
    assert len(records) == 1
    assert records[0].status == NotificationStatus.SENT
    assert records[0].kind == NotificationKind.BOOKING_STATUS_NOTICE
    assert client.sent[0].template_name == "booking_status_notice_de"
    assert client.sent[0].template_params[0] == "Neue Buchung"
    assert client.sent[0].template_params[1] == "Apartment Mitte"


def test_dispatch_cancellation_uses_status_template(mock_db) -> None:
    """Storno → Status-Template."""
    client = MockWhatsAppClient()
    svc = _notification_svc(mock_db, client)
    extraction = BookingExtraction(
        intent=BookingIntent.CANCELLATION,
        property_name="Loft Nord",
        guest_name="Max Mustermann",
        booking_number="BK-9",
        check_in=date(2026, 7, 1),
        check_out=date(2026, 7, 5),
    )
    records = svc.dispatch_after_approval("corr-3", extraction)
    assert records[0].kind == NotificationKind.BOOKING_STATUS_NOTICE
    assert client.sent[0].template_params[0] == "Storno"
    assert client.sent[0].template_params[4] == "Max Mustermann"


def test_dispatch_guest_inquiry_uses_inquiry_template(mock_db) -> None:
    """Gastnachricht → guest_inquiry-Template."""
    client = MockWhatsAppClient()
    svc = _notification_svc(mock_db, client)
    extraction = BookingExtraction(
        intent=BookingIntent.GUEST_INQUIRY,
        property_name="Apartment Mitte",
        guest_name="Anna Schmidt",
        booking_number="AB400",
        check_in=date(2026, 8, 1),
        check_out=date(2026, 8, 5),
    )
    records = svc.dispatch_after_approval("corr-guest", extraction)
    assert records[0].kind == NotificationKind.BOOKING_GUEST_INQUIRY
    assert client.sent[0].template_name == "booking_guest_inquiry_de"
    assert client.sent[0].template_params[0] == "Gastnachricht"
    assert client.sent[0].template_params[1] == "Apartment Mitte"
    assert client.sent[0].template_params[5] == "Anna Schmidt"


def test_dispatch_complaint_uses_inquiry_template_with_label(mock_db) -> None:
    """Beschwerde → gleiches Template, Label Beschwerde."""
    client = MockWhatsAppClient()
    svc = _notification_svc(mock_db, client)
    extraction = BookingExtraction(
        intent=BookingIntent.COMPLAINT,
        property_name="Loft Süd",
        guest_name="Tom Weber",
        booking_number="BK-44",
    )
    records = svc.dispatch_after_approval("corr-complaint", extraction)
    assert records[0].kind == NotificationKind.BOOKING_GUEST_INQUIRY
    assert client.sent[0].template_params[0] == "Beschwerde"


def test_idempotency_prevents_duplicate_send(mock_db) -> None:
    """Retry nach Freigabe sendet nicht doppelt."""
    client = MockWhatsAppClient()
    svc = _notification_svc(mock_db, client)
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Studio",
        booking_number="X1",
    )
    first = svc.dispatch_after_approval("corr-4", extraction)
    second = svc.dispatch_after_approval("corr-4", extraction)
    assert len(first) == 1
    assert second == []
    assert len(client.sent) == 1


def test_property_recipients_are_included(mock_db) -> None:
    """Unterkunftsspezifische Cleaner-Nummern werden berücksichtigt."""
    client = MockWhatsAppClient()
    property_repo = PropertyRecipientRepository(mock_db)
    account_id = "test-account"
    from backend.infrastructure.repositories.property_recipient_repository import (
        PropertyWhatsAppEmployee,
    )

    property_repo.upsert(
        account_id,
        "Apartment Mitte",
        [PropertyWhatsAppEmployee(phone_e164="+491709999999", locale="de")],
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
    )
    records = svc.dispatch_after_approval("corr-5", extraction, account_id=account_id)
    assert len(records) == 1
    assert records[0].recipient_e164 == "+491709999999"


def test_cancellation_skips_property_cleaners(mock_db) -> None:
    """Storno benachrichtigt Host, nicht Putzfrau der Unterkunft."""
    client = MockWhatsAppClient()
    property_repo = PropertyRecipientRepository(mock_db)
    account_id = "test-account"
    from backend.infrastructure.repositories.property_recipient_repository import (
        PropertyWhatsAppEmployee,
    )

    property_repo.upsert(
        account_id,
        "Apartment Mitte",
        [PropertyWhatsAppEmployee(phone_e164="+491709999999", locale="de")],
    )
    svc = NotificationService(
        _settings(WHATSAPP_DEFAULT_RECIPIENTS="+491701234567"),
        NotificationRepository(mock_db),
        UserRepository(mock_db),
        property_repo,
        PlatformSettingsRepository(mock_db),
        whatsapp_client=client,
    )
    extraction = BookingExtraction(
        intent=BookingIntent.CANCELLATION,
        property_name="Apartment Mitte",
        booking_number="AB200",
    )
    records = svc.dispatch_after_approval(
        "corr-storno", extraction, account_id=account_id
    )
    assert len(records) == 1
    assert records[0].recipient_e164 == "+491701234567"


def test_disabled_client_marks_skipped_when_enabled_flag_true(mock_db) -> None:
    """WHATSAPP_ENABLED=true aber DisabledWhatsAppClient → SKIPPED (Dry-Run-Schutz)."""
    svc = _notification_svc(mock_db, DisabledWhatsAppClient())
    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Studio",
        booking_number="Z9",
    )
    records = svc.dispatch_after_approval("corr-6", extraction)
    assert records[0].status == NotificationStatus.SKIPPED


def test_workflow_finalize_triggers_whatsapp_on_approval(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    """Freigabe im Workflow löst NotificationService aus."""

    from backend.ai.services.classification import ClassificationService
    from backend.ai.services.extraction import ExtractionService
    from backend.ai.services.grounding import GroundingService
    from backend.ai.services.response_generation import ResponseGenerationService
    from backend.ai.services.retrieval import RetrievalService
    from backend.ai.services.validation import ValidationService
    from backend.ai.workflows.email_workflow import EmailWorkflow
    from backend.core.models.email import IncomingEmail, ProcessingState
    from tests.mocks import MockLLM

    client = MockWhatsAppClient()
    notification_svc = _notification_svc(mock_db, client)
    llm = MockLLM()
    retrieval = RetrievalService(entity_repo, email_repo)
    wf = EmailWorkflow(
        ingestion=ingestion_service,
        classification=ClassificationService(llm, "gpt-4o-mini"),
        extraction=ExtractionService(llm, "gpt-4o-mini"),
        validation=ValidationService(),
        retrieval=retrieval,
        response_gen=ResponseGenerationService(
            llm,
            "gpt-4o",
            retrieval,
            GroundingService(),
        ),
        email_repo=email_repo,
        extraction_repo=extraction_repo,
        indexing=None,
        notification_service=notification_svc,
    )
    payload = IncomingEmail(
        message_id="wf-wa-001",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Stornierung AB200 bitte.",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    wf.run(payload, thread_id=payload.correlation_id)
    wf.resume_after_approval(payload.correlation_id, approved_body="OK")
    assert len(client.sent) >= 1
    email = email_repo.get_by_message_id("wf-wa-001")
    assert email is not None
    assert email.processing_state == ProcessingState.APPROVED

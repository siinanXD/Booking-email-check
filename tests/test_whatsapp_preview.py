"""WhatsApp-Review-Vorschau mit Mehrsprachigkeit."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.features.notifications.notification_preview import build_whatsapp_preview
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
    PropertyWhatsAppEmployee,
)
from backend.infrastructure.repositories.user_repository import UserRepository


def _preview_ctx(mock_db: object) -> AppContext:
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "test",
            "MONGODB_URI": "mongodb://localhost:27017",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_DEFAULT_RECIPIENTS": "",
        }
    )
    return AppContext(
        settings=settings,
        db=mock_db,  # type: ignore[arg-type]
        ingestion_router=None,  # type: ignore[arg-type]
        review_router=None,  # type: ignore[arg-type]
        workflow=None,  # type: ignore[arg-type]
        email_repo=None,  # type: ignore[arg-type]
        extraction_repo=None,  # type: ignore[arg-type]
        review_repo=None,  # type: ignore[arg-type]
        metrics_repo=None,  # type: ignore[arg-type]
        user_repo=UserRepository(mock_db),  # type: ignore[arg-type]
        account_repo=None,  # type: ignore[arg-type]
        revoked_token_repo=None,  # type: ignore[arg-type]
        platform_settings_repo=PlatformSettingsRepository(mock_db),  # type: ignore[arg-type]
        property_recipient_repo=PropertyRecipientRepository(mock_db),  # type: ignore[arg-type]
        mail_connection_repo=None,  # type: ignore[arg-type]
        outlook_oauth_flow_repo=None,  # type: ignore[arg-type]
        platform_llm_config_repo=None,  # type: ignore[arg-type]
        platform_llm_prompt_history_repo=None,  # type: ignore[arg-type]
        tenant_workflow_repo=None,  # type: ignore[arg-type]
        admin_audit_log_repo=None,  # type: ignore[arg-type]
        mail_summary_repo=None,  # type: ignore[arg-type]
        tenant_learned_examples_repo=None,  # type: ignore[arg-type]
        support_ticket_repo=None,  # type: ignore[arg-type]
        platform_admin_config_repo=None,  # type: ignore[arg-type]
        indexing_service=None,
    )


def test_preview_includes_generated_body_and_german_translation(mock_db) -> None:
    ctx = _preview_ctx(mock_db)
    account_id = "preview-account"
    property_repo = PropertyRecipientRepository(mock_db)
    property_repo.upsert(
        account_id,
        "Apartment Mitte",
        [PropertyWhatsAppEmployee(phone_e164="+491709999999", locale="pl")],
    )

    extraction = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Apartment Mitte",
        booking_number="AB100",
        check_in=date(2026, 6, 10),
        check_out=date(2026, 6, 15),
    )
    preview = build_whatsapp_preview(
        ctx,
        account_id,
        "corr-preview",
        extraction,
    )

    assert preview.enabled is True
    assert len(preview.messages) == 1
    msg = preview.messages[0]
    assert msg.recipient_role == "employee"
    assert msg.template_language == "pl"
    assert "Masz nowe zlecenie sprzątania" in msg.generated_body
    assert "Neue Reinigungsaufgabe für dein Team" in msg.generated_body_de
    assert msg.generated_body != msg.generated_body_de

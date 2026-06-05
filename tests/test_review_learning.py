"""Tests für Lernen aus freigegebenen Reviews."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.core.models.email import StoredEmail
from backend.features.review.review_learning import learn_from_approved_review
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.platform_admin_config_repository import (
    PlatformAdminConfigRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository
from backend.infrastructure.repositories.support_ticket_repository import (
    SupportTicketRepository,
)
from backend.infrastructure.repositories.tenant_learned_examples_repository import (
    TenantLearnedExamplesRepository,
)


def _ctx(mock_db: object) -> AppContext:
    settings = Settings()
    return AppContext(
        settings=settings,
        db=mock_db,  # type: ignore[arg-type]
        ingestion_router=None,  # type: ignore[arg-type]
        review_router=None,  # type: ignore[arg-type]
        workflow=None,  # type: ignore[arg-type]
        email_repo=EmailRepository(mock_db),  # type: ignore[arg-type]
        extraction_repo=ExtractionRepository(mock_db),  # type: ignore[arg-type]
        review_repo=ReviewRepository(mock_db),  # type: ignore[arg-type]
        metrics_repo=None,  # type: ignore[arg-type]
        user_repo=None,  # type: ignore[arg-type]
        account_repo=None,  # type: ignore[arg-type]
        revoked_token_repo=None,  # type: ignore[arg-type]
        platform_settings_repo=None,  # type: ignore[arg-type]
        property_recipient_repo=None,  # type: ignore[arg-type]
        mail_connection_repo=None,  # type: ignore[arg-type]
        outlook_oauth_flow_repo=None,  # type: ignore[arg-type]
        platform_llm_config_repo=None,  # type: ignore[arg-type]
        platform_llm_prompt_history_repo=None,  # type: ignore[arg-type]
        tenant_workflow_repo=None,  # type: ignore[arg-type]
        admin_audit_log_repo=None,  # type: ignore[arg-type]
        mail_summary_repo=None,  # type: ignore[arg-type]
        tenant_learned_examples_repo=TenantLearnedExamplesRepository(mock_db),  # type: ignore[arg-type]
        support_ticket_repo=SupportTicketRepository(mock_db),  # type: ignore[arg-type]
        platform_admin_config_repo=PlatformAdminConfigRepository(mock_db),  # type: ignore[arg-type]
        indexing_service=None,
    )


def test_learn_from_approved_stores_example(mock_db: object) -> None:
    """Freigabe speichert Mandanten-Few-Shot."""
    ctx = _ctx(mock_db)
    account_id = "acc-learn"
    email = StoredEmail(
        message_id="m-learn",
        from_address="guest@test.local",
        subject="Anfrage",
        body_text="ich würde gerne buchen",
        received_at=datetime.now(UTC),
        correlation_id="corr-learn",
        account_id=account_id,
    )
    ctx.email_repo.upsert_by_message_id(email)
    ctx.extraction_repo.save(
        "corr-learn",
        "m-learn",
        BookingExtraction(intent=BookingIntent.NEW_BOOKING, guest_name="Max"),
        account_id=account_id,
    )
    ctx.review_repo.upsert_pending(
        correlation_id="corr-learn",
        message_id="m-learn",
        draft_body="Entwurf",
        grounding_flag=True,
        intent="new_booking",
        account_id=account_id,
    )
    learn_from_approved_review(
        ctx,
        account_id,
        "corr-learn",
        "Freigegebene Antwort",
    )
    examples = ctx.tenant_learned_examples_repo.list_recent(account_id)
    assert len(examples) == 1
    assert examples[0]["intent"] == "new_booking"

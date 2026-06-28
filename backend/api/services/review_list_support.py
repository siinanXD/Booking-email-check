"""Mapping Review-Datensätze → API-Queue-Items."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.review_eligibility import is_review_queue_eligible
from backend.api.schemas.review import ReviewQueueItem
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRecord


def workflow_id_for(
    extraction_repo: ExtractionRepository,
    correlation_id: str,
    *,
    account_id: str,
) -> str | None:
    """Lädt workflow_id aus Extraktions-Dokument."""
    return extraction_repo.get_workflow_id(correlation_id, account_id=account_id)


def record_to_queue_item_from_maps(
    record: ReviewRecord,
    *,
    email: StoredEmail | None,
    ext: BookingExtraction | None,
    workflow_id: str | None,
    allow_ineligible: bool = False,
) -> ReviewQueueItem | None:
    """Baut Queue-Item aus vorgeladenen Maps; None wenn nicht eligible."""
    if email is None:
        return None
    eligible, _ = is_review_queue_eligible(email, ext, workflow_id=workflow_id)
    if not allow_ineligible and not eligible and record.review_status == "pending":
        return None
    return ReviewQueueItem(
        correlation_id=record.correlation_id,
        message_id=record.message_id,
        subject=email.subject,
        from_address=email.from_address,
        intent=record.intent,
        draft_body=record.draft_body,
        grounding_flag=record.grounding_flag,
        review_status=record.review_status,
        received_at=email.received_at.isoformat() if email.received_at else None,
        confidence=record.confidence,
        escalated=record.escalated,
        signals=list(record.signals),
        grounding_span=record.grounding_span,
        source_flags=list(record.source_flags),
    )


def record_to_queue_item(
    ctx: AppContext,
    account_id: str,
    record: ReviewRecord,
    *,
    allow_ineligible: bool = False,
) -> ReviewQueueItem | None:
    """Baut Queue-Item; None wenn E-Mail fehlt oder nicht eligible."""
    email = ctx.email_repo.get_by_correlation_id(
        record.correlation_id,
        account_id=account_id,
    )
    if email is None:
        return None
    ext = ctx.extraction_repo.get_by_correlation_id(
        record.correlation_id,
        account_id=account_id,
    )
    wf_id = workflow_id_for(
        ctx.extraction_repo,
        record.correlation_id,
        account_id=account_id,
    )
    return record_to_queue_item_from_maps(
        record,
        email=email,
        ext=ext,
        workflow_id=wf_id,
        allow_ineligible=allow_ineligible,
    )

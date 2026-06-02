"""Review-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from models.email import ProcessingState, StoredEmail
from repositories.review_repository import ReviewRepository
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


def test_review_approve_calls_workflow(
    client: Any,
    auth_headers: dict[str, str],
    email_repo: Any,
    extraction_repo: Any,
    app: Any,
) -> None:
    """Approve ruft review_router.approve_draft auf."""
    email = StoredEmail(
        message_id="m2@test",
        from_address="guest@test.com",
        subject="Storno",
        body_text="Bitte stornieren",
        received_at=datetime.now(UTC),
        correlation_id="corr-approve",
        processing_state=ProcessingState.PENDING_REVIEW,
        updated_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(email)
    extraction_repo.save(
        "corr-approve",
        "m2@test",
        BookingExtraction(intent=BookingIntent.CANCELLATION),
    )
    review_repo: ReviewRepository = app.extensions["ctx"].review_repo
    review_repo.upsert_pending(
        correlation_id="corr-approve",
        message_id="m2@test",
        draft_body="Entwurf",
        grounding_flag=False,
        intent="cancellation",
    )
    ctx = app.extensions["ctx"]
    with patch.object(
        ctx.review_router,
        "approve_draft",
        return_value={"review": {"status": "approved"}},
    ) as mock_approve:
        resp = client.post(
            "/api/review/approve",
            headers=auth_headers,
            json={
                "correlation_id": "corr-approve",
                "approved_body": "Freigegeben",
            },
        )
    assert resp.status_code == 200
    mock_approve.assert_called_once()


def test_review_reject_calls_workflow(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """Reject ruft reject_draft auf."""
    ctx = app.extensions["ctx"]
    with patch.object(
        ctx.review_router,
        "reject_draft",
        return_value={"review": {"status": "rejected"}},
    ) as mock_reject:
        resp = client.post(
            "/api/review/reject",
            headers=auth_headers,
            json={"correlation_id": "corr-x", "reason": "Nicht passend"},
        )
    assert resp.status_code == 200
    mock_reject.assert_called_once()

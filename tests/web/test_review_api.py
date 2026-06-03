"""Review-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository


def test_list_pending_reviews(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """GET /api/reviews liefert pending Einträge mit Extraktion."""
    cid = "corr-review-1"
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-review@test",
            from_address="bookings@beds24.com",
            subject="Nachricht vom Gast - Buchung 12345",
            body_text="Frage zur Buchung",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            platform="beds24",
            account_id=tenant_account_id,
        )
    )
    extraction_repo.save(
        cid,
        "m-review@test",
        BookingExtraction(
            intent=BookingIntent.GUEST_INQUIRY,
            booking_number="12345",
        ),
        account_id=tenant_account_id,
    )
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    reviews.upsert_pending(
        correlation_id=cid,
        message_id="m-review@test",
        draft_body="Hallo Gast, vielen Dank fuer Ihre Anfrage.",
        grounding_flag=False,
        intent="guest_inquiry",
        account_id=tenant_account_id,
    )
    resp = client.get("/api/review/pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert any(
        item["correlation_id"] == cid and "Hallo Gast" in item["draft_body"]
        for item in data["items"]
    )


def test_reject_review(
    app: object,
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """POST /api/review/reject lehnt ausstehenden Entwurf ab."""
    from datetime import UTC, datetime

    from backend.core.models.email import IncomingEmail

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    payload = IncomingEmail(
        message_id="m-reject-api",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Stornierung AB200 bitte.",
        received_at=datetime.now(UTC),
        platform="airbnb",
        account_id=tenant_account_id,
    )
    ctx.workflow.run(payload, thread_id=payload.correlation_id)
    resp = client.post(
        "/api/review/reject",
        json={
            "correlation_id": payload.correlation_id,
            "reason": "Not acceptable",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "rejected"
    email = ctx.email_repo.get_by_message_id("m-reject-api")
    assert email is not None
    assert email.processing_state == ProcessingState.REJECTED

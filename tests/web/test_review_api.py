"""Review-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.email import ProcessingState, StoredEmail
from repositories.extraction_repository import ExtractionRepository
from repositories.review_repository import ReviewRepository
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


def test_list_pending_reviews(
    client: Any,
    auth_headers: dict[str, str],
    mock_db: object,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
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
        )
    )
    extraction_repo.save(
        cid,
        "m-review@test",
        BookingExtraction(
            intent=BookingIntent.GUEST_INQUIRY,
            booking_number="12345",
        ),
    )
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    reviews.upsert_pending(
        correlation_id=cid,
        message_id="m-review@test",
        draft_body="Hallo Gast, vielen Dank fuer Ihre Anfrage.",
        grounding_flag=False,
        intent="guest_inquiry",
    )
    resp = client.get("/api/review/pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert any(
        item["correlation_id"] == cid and "Hallo Gast" in item["draft_body"]
        for item in data["items"]
    )

"""Dashboard-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.email import ProcessingState, StoredEmail
from repositories.extraction_repository import ExtractionRepository
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


def test_dashboard_stats_empty(client: Any, auth_headers: dict[str, str]) -> None:
    """Leere DB liefert Null-Stats."""
    resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pending_review"] == 0
    assert data["total_emails_today"] == 0


def test_dashboard_stats_with_mail(
    client: Any,
    auth_headers: dict[str, str],
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """Mail in DB erhöht Zähler."""
    email = StoredEmail(
        message_id="m1@test",
        from_address="a@b.com",
        subject="Buchung",
        body_text="hi",
        received_at=datetime.now(UTC),
        correlation_id="corr-1",
        processing_state=ProcessingState.PENDING_REVIEW,
        updated_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(email)
    extraction_repo.save(
        "corr-1",
        "m1@test",
        BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="AB1"),
    )
    resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_emails_today"] >= 1

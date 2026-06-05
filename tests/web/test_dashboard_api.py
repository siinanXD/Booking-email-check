"""Dashboard-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)


def test_dashboard_stats_empty(client: Any, auth_headers: dict[str, str]) -> None:
    """Leere DB liefert Null-Stats."""
    resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pending_review"] == 0
    assert data["nav_ground_zero"] == 0
    assert data["total_emails_today"] == 0
    assert data["reviewed_today"] == 0
    assert data["last_sync_at"] is None


def test_dashboard_stats_with_mail(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
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
        account_id=tenant_account_id,
    )
    email_repo.upsert_by_message_id(email)
    extraction_repo.save(
        "corr-1",
        "m1@test",
        BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="AB1"),
        account_id=tenant_account_id,
    )
    resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_emails_today"] >= 1
    assert data["booking_emails_total"] >= 1
    assert data["booking_emails_week"] >= 1
    assert data["nav_bookings"] >= 1
    assert data["new_bookings_today"] >= 1

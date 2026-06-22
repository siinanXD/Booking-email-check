"""Buchungslisten-API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.ai.domain.booking.booking_relevance import relevance_fields
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)


def _persist_relevance(
    email_repo: Any,
    email: StoredEmail,
    extraction: BookingExtraction,
    account_id: str,
) -> None:
    """Schreibt die vorberechneten Relevanz-Felder wie der Workflow im extract()."""
    email_repo.update_processing_state(
        email.message_id,
        ProcessingState.EXTRACTED,
        account_id=account_id,
        **relevance_fields(email, extraction),
    )


def test_list_bookings(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """GET /api/bookings liefert new_booking mit Extraktion."""
    cid = "corr-booking-api"
    email = StoredEmail(
        message_id="m-booking@test",
        from_address="bookings@beds24.com",
        subject="Neue Buchung AB99",
        body_text="Reservierung bestätigt",
        received_at=datetime.now(UTC),
        correlation_id=cid,
        processing_state=ProcessingState.CLASSIFIED,
        platform="beds24",
        account_id=tenant_account_id,
    )
    email_repo.upsert_by_message_id(email)
    ext = BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="AB99")
    extraction_repo.save(cid, "m-booking@test", ext, account_id=tenant_account_id)
    _persist_relevance(email_repo, email, ext, tenant_account_id)
    resp = client.get("/api/bookings/?limit=20", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert any(item["correlation_id"] == cid for item in data["items"])


def test_list_bookings_with_beds24_subject_and_other_intent(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """Buchungsliste zeigt Beds24-Mails auch wenn LLM intent=other lieferte."""
    cid = "corr-beds24-other"
    email = StoredEmail(
        message_id="m-beds24-other@test",
        from_address="bookings@beds24.com",
        subject="Buchung: Münzbach Ferienzimmer : Zimmer Nr. 4",
        body_text="Reservierung",
        received_at=datetime.now(UTC),
        correlation_id=cid,
        processing_state=ProcessingState.VALIDATED,
        platform="beds24",
        account_id=tenant_account_id,
    )
    email_repo.upsert_by_message_id(email)
    ext = BookingExtraction(intent=BookingIntent.OTHER)
    extraction_repo.save(cid, "m-beds24-other@test", ext, account_id=tenant_account_id)
    _persist_relevance(email_repo, email, ext, tenant_account_id)
    resp = client.get("/api/bookings/?limit=20", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(item["correlation_id"] == cid for item in data["items"])
    match = next(i for i in data["items"] if i["correlation_id"] == cid)
    assert match["intent"] == "new_booking"

"""E-Mail-Listen-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.email import ProcessingState, StoredEmail
from repositories.extraction_repository import ExtractionRepository
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


def test_list_emails_by_intents(
    client: Any,
    auth_headers: dict[str, str],
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """intents-Parameter filtert mehrere Intent-Typen."""
    for i, intent in enumerate(
        (BookingIntent.OTHER, BookingIntent.GUEST_INQUIRY),
        start=1,
    ):
        cid = f"corr-intent-{i}"
        email_repo.upsert_by_message_id(
            StoredEmail(
                message_id=f"m{i}@test",
                from_address="a@b.com",
                subject=f"Mail {i}",
                body_text="hi",
                received_at=datetime.now(UTC),
                correlation_id=cid,
                processing_state=ProcessingState.CLASSIFIED,
            )
        )
        extraction_repo.save(
            cid,
            f"m{i}@test",
            BookingExtraction(intent=intent),
        )

    resp = client.get(
        "/api/emails/?intents=other,guest_inquiry",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 2
    returned = {item["intent"] for item in data["items"]}
    assert returned == {"other", "guest_inquiry"}


def test_list_emails_without_intent_filter(
    client: Any,
    auth_headers: dict[str, str],
    email_repo: Any,
) -> None:
    """Ohne Intent-Filter erscheinen auch Mails ohne Extraktion."""
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-noext@test",
            from_address="a@b.com",
            subject="Ohne Extraktion",
            body_text="hi",
            received_at=datetime.now(UTC),
            correlation_id="corr-noext",
            processing_state=ProcessingState.RECEIVED,
        )
    )
    resp = client.get("/api/emails/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total"] >= 1

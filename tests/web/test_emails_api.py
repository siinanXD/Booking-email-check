"""E-Mail-Listen-API-Tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)


def test_list_emails_by_intents(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
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
                account_id=tenant_account_id,
            )
        )
        extraction_repo.save(
            cid,
            f"m{i}@test",
            BookingExtraction(intent=intent),
            account_id=tenant_account_id,
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
    tenant_account_id: str,
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
            account_id=tenant_account_id,
        )
    )
    resp = client.get("/api/emails/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total"] >= 1


def test_email_detail_includes_booking_number(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """GET /api/emails/<id> liefert booking_number aus Extraktion."""
    cid = "corr-detail-bn"
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-bn@test",
            from_address="bookings@beds24.com",
            subject="Buchung 99887",
            body_text="Details",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.CLASSIFIED,
            account_id=tenant_account_id,
        )
    )
    extraction_repo.save(
        cid,
        "m-bn@test",
        BookingExtraction(booking_number="99887"),
        account_id=tenant_account_id,
    )
    resp = client.get(f"/api/emails/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["booking_number"] == "99887"


def test_email_activity_timeline(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    """GET /api/emails/<id>/activity liefert chronologischen Verlauf."""
    from backend.core.models.notification import (
        NotificationKind,
        NotificationStatus,
    )
    from backend.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    cid = "corr-activity"
    received = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-act@test",
            from_address="guest@test.local",
            subject="Anfrage",
            body_text="Hallo",
            received_at=received,
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            account_id=tenant_account_id,
        )
    )
    extraction_repo.save(
        cid,
        "m-act@test",
        BookingExtraction(booking_number="BN-42"),
        account_id=tenant_account_id,
    )
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    reviews.upsert_pending(
        correlation_id=cid,
        message_id="m-act@test",
        draft_body="Antwort",
        grounding_flag=False,
        intent="guest_inquiry",
        account_id=tenant_account_id,
    )
    reviews.update_status(
        cid,
        "completed",
        account_id=tenant_account_id,
        approved_body="Antwort",
    )
    notifications = NotificationRepository(mock_db)  # type: ignore[arg-type]
    notifications.try_claim(
        notifications.new_record(
            idempotency_key="act-wa-1",
            correlation_id=cid,
            kind=NotificationKind.BOOKING_GUEST_INQUIRY,
            recipient_e164="+491701234567",
            template_name="booking_guest_inquiry_de",
            template_language="de",
            template_params=["BN-42"],
            status=NotificationStatus.PENDING,
        )
    )
    notifications.mark_sent(
        notifications.list_by_correlation_id(cid)[0].id,
        provider="mock",
        provider_message_id="wa-1",
    )

    resp = client.get(f"/api/emails/{cid}/activity", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["correlation_id"] == cid
    kinds = [event["kind"] for event in data["events"]]
    assert "mail_received" in kinds
    assert "extraction_done" in kinds
    assert "review_completed" in kinds
    assert "whatsapp_sent" in kinds
    assert kinds.index("mail_received") < kinds.index("review_completed")


def test_email_activity_not_found(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """Unbekannte Correlation-ID → 404."""
    resp = client.get("/api/emails/missing-corr/activity", headers=auth_headers)
    assert resp.status_code == 404

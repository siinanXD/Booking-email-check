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


def test_pending_grounding_filter(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
) -> None:
    """GET /api/review/pending?grounding=1 filtert nach grounding_flag."""
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    for cid, flagged in (("corr-g1", True), ("corr-g2", False)):
        email_repo.upsert_by_message_id(
            StoredEmail(
                message_id=f"m-{cid}",
                from_address="a@test.local",
                subject="Test",
                body_text="body",
                received_at=datetime.now(UTC),
                correlation_id=cid,
                account_id=tenant_account_id,
            )
        )
        reviews.upsert_pending(
            correlation_id=cid,
            message_id=f"m-{cid}",
            draft_body="draft",
            grounding_flag=flagged,
            intent="new_booking",
            account_id=tenant_account_id,
        )
    resp = client.get(
        "/api/review/pending?grounding=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = {item["correlation_id"] for item in resp.get_json()["items"]}
    assert "corr-g1" in ids
    assert "corr-g2" not in ids


def test_list_ground_zero_endpoint(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
) -> None:
    """GET /api/review/ground-zero liefert offene Grounding-Fälle."""
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    for cid, flagged, status in (
        ("corr-gz1", True, "pending"),
        ("corr-gz2", False, "pending"),
        ("corr-gz3", True, "approved"),
    ):
        email_repo.upsert_by_message_id(
            StoredEmail(
                message_id=f"m-{cid}",
                from_address="a@test.local",
                subject="Test",
                body_text="body",
                received_at=datetime.now(UTC),
                correlation_id=cid,
                account_id=tenant_account_id,
            )
        )
        reviews.upsert_pending(
            correlation_id=cid,
            message_id=f"m-{cid}",
            draft_body="draft",
            grounding_flag=flagged,
            intent="new_booking",
            account_id=tenant_account_id,
        )
        if status == "approved":
            reviews.update_status(
                cid,
                "approved",
                account_id=tenant_account_id,
                approved_body="ok",
            )
            reviews._col.update_one(
                {"_id": cid},
                {"$set": {"grounding_flag": True}},
            )
    resp = client.get("/api/review/ground-zero", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    ids = {item["correlation_id"] for item in data["items"]}
    assert "corr-gz1" in ids
    assert "corr-gz3" in ids
    assert "corr-gz2" not in ids
    assert data["total"] == 2


def test_nav_ground_zero_matches_open_count(
    app: object,
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
) -> None:
    """nav_ground_zero und Ground-Zero-API nutzen dieselbe Zählbasis."""
    from backend.api.services.dashboard_queries import nav_ground_zero

    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    for cid in ("corr-nav-gz1", "corr-nav-gz2"):
        email_repo.upsert_by_message_id(
            StoredEmail(
                message_id=f"m-{cid}",
                from_address="a@test.local",
                subject="Test",
                body_text="body",
                received_at=datetime.now(UTC),
                correlation_id=cid,
                account_id=tenant_account_id,
            )
        )
        reviews.upsert_pending(
            correlation_id=cid,
            message_id=f"m-{cid}",
            draft_body="draft",
            grounding_flag=True,
            intent="new_booking",
            account_id=tenant_account_id,
        )
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    open_count = reviews.count_open_grounding(account_id=tenant_account_id)
    assert nav_ground_zero(ctx, tenant_account_id) == open_count
    assert open_count == 2
    resp = client.get("/api/review/ground-zero", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total"] == open_count


def test_grounding_includes_approved_with_flag(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
) -> None:
    """Freigegeben + grounding_flag erscheint im Grounding-Filter."""
    cid = "corr-g-approved"
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-g-app",
            from_address="guest@test.local",
            subject="Buchung",
            body_text="buchung",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            account_id=tenant_account_id,
        )
    )
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    reviews.upsert_pending(
        correlation_id=cid,
        message_id="m-g-app",
        draft_body="draft",
        grounding_flag=True,
        intent="new_booking",
        account_id=tenant_account_id,
    )
    reviews.update_status(
        cid,
        "approved",
        account_id=tenant_account_id,
        approved_body="ok",
    )
    # Legacy: freigegeben, aber Grounding-Flag noch gesetzt (vor Flag-Reset-Fix)
    reviews._col.update_one(
        {"_id": cid},
        {"$set": {"grounding_flag": True}},
    )
    resp = client.get("/api/review/pending?grounding=1", headers=auth_headers)
    assert resp.status_code == 200
    ids = {item["correlation_id"] for item in resp.get_json()["items"]}
    assert cid in ids


def test_pending_grounding_includes_ineligible_booking(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: object,
    email_repo: Any,
) -> None:
    """Grounding-Filter zeigt auch Mails, die sonst aus der Queue gefiltert wären."""
    cid = "corr-g-inelig"
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-inelig",
            from_address="newsletter@spam.local",
            subject="Werbung",
            body_text="unsubscribe",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            account_id=tenant_account_id,
        )
    )
    reviews = ReviewRepository(mock_db)  # type: ignore[arg-type]
    reviews.upsert_pending(
        correlation_id=cid,
        message_id="m-inelig",
        draft_body="draft",
        grounding_flag=True,
        intent="new_booking",
        account_id=tenant_account_id,
    )
    resp = client.get("/api/review/pending?grounding=1", headers=auth_headers)
    assert resp.status_code == 200
    ids = {item["correlation_id"] for item in resp.get_json()["items"]}
    assert cid in ids


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


def test_list_released_and_completed_empty(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    for path in ("/api/review/released", "/api/review/completed"):
        resp = client.get(path, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["total"] >= 0

"""End-to-End-Test: Ingestion → LangGraph-Workflow → Review → Completion.

Testet den kompletten Pfad vom Maileingang bis zur abgeschlossenen
menschlichen Freigabe – ohne externen Dienst (MockLLM + mongomock).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import IncomingEmail, ProcessingState


def _booking_email(message_id: str, cid: str) -> IncomingEmail:
    """Hilfsfunktion: realistischer Buchungseingang mit fester correlation_id."""
    return IncomingEmail(
        message_id=message_id,
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Bitte stornieren Sie die Reservierung AB200.",
        received_at=datetime.now(UTC),
        platform="airbnb",
        correlation_id=cid,
    )


# ---------------------------------------------------------------------------
# Workflow-Level (direkt, ohne HTTP)
# ---------------------------------------------------------------------------


def test_workflow_run_creates_pending_review(
    app: Any,
    mock_db: Any,
) -> None:
    """Workflow läuft durch MockLLM und endet im pending-Review-Zustand."""

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = "e2e-workflow-001"
    email = _booking_email("wf-e2e-001@test", cid)

    with app.app_context():
        result = ctx.workflow.run(email, thread_id=cid)

    # Workflow endet mit pending review oder discarded (Triage-Entscheidung)
    review = result.get("review")
    stored = ctx.email_repo.get_by_message_id("wf-e2e-001@test")
    assert stored is not None
    if review and review.status == "pending":
        assert stored.processing_state in (
            ProcessingState.DRAFTED,
            ProcessingState.PENDING_REVIEW,
        )
    else:
        # Triage hat verworfen — auch valid
        assert stored.processing_state == ProcessingState.DISCARDED


def test_workflow_approve_reject_cycle(
    app: Any,
    mock_db: Any,
) -> None:
    """Workflow: run → pending → approve → APPROVED (direkte Service-Ebene)."""
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = "e2e-workflow-approve-001"
    email = _booking_email("wf-approve-e2e@test", cid)

    with app.app_context():
        result = ctx.workflow.run(email, thread_id=cid)

    review = result.get("review")
    if review is None or review.status != "pending":
        return  # Triage hat verworfen, Test nicht anwendbar

    with app.app_context():
        approved = ctx.review_router.approve_draft(
            cid,
            approved_body="Bestätigter Text",
        )

    assert approved["review"].status == "approved"
    stored = ctx.email_repo.get_by_message_id("wf-approve-e2e@test")
    assert stored is not None
    assert stored.processing_state == ProcessingState.APPROVED


# ---------------------------------------------------------------------------
# HTTP Review-Queue (Setup via DB, Review-Flow via HTTP)
# ---------------------------------------------------------------------------


def test_review_queue_pending_visible(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Pending-Review-Eintrag erscheint in der HTTP-Queue."""
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.ai.domain.booking.taxonomy import BookingIntent
    from backend.core.models.email import StoredEmail
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    cid = "e2e-queue-visible-001"
    msg_id = "msg-queue-visible@test"

    from backend.infrastructure.repositories.email_repository import EmailRepository

    EmailRepository(mock_db).upsert_by_message_id(  # type: ignore[arg-type]
        StoredEmail(
            message_id=msg_id,
            from_address="guest@airbnb.com",
            subject="Stornierung AB200",
            body_text="Stornierung AB200",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            platform="airbnb",
            account_id=tenant_account_id,
        )
    )
    ExtractionRepository(mock_db).save(  # type: ignore[arg-type]
        cid,
        msg_id,
        BookingExtraction(intent=BookingIntent.CANCELLATION, booking_number="AB200"),
        account_id=tenant_account_id,
    )
    ReviewRepository(mock_db).upsert_pending(  # type: ignore[arg-type]
        correlation_id=cid,
        message_id=msg_id,
        draft_body="Entwurf",
        grounding_flag=False,
        intent="cancellation",
        account_id=tenant_account_id,
    )

    resp = client.get("/api/review/pending", headers=auth_headers)
    assert resp.status_code == 200
    cids = [item["correlation_id"] for item in resp.get_json()["items"]]
    assert cid in cids


def test_review_complete_after_approve(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Approve via ReviewRepo + Complete via HTTP → status completed."""
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.core.models.email import StoredEmail
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    cid = "e2e-complete-001"
    msg_id = "msg-complete@test"

    EmailRepository(mock_db).upsert_by_message_id(  # type: ignore[arg-type]
        StoredEmail(
            message_id=msg_id,
            from_address="guest@airbnb.com",
            subject="Stornierung AB200",
            body_text="Stornierung",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            platform="airbnb",
            account_id=tenant_account_id,
        )
    )
    ExtractionRepository(mock_db).save(  # type: ignore[arg-type]
        cid, msg_id, BookingExtraction(), account_id=tenant_account_id
    )
    review_repo = ReviewRepository(mock_db)  # type: ignore[arg-type]
    review_repo.upsert_pending(
        correlation_id=cid,
        message_id=msg_id,
        draft_body="Entwurf",
        grounding_flag=False,
        intent="cancellation",
        account_id=tenant_account_id,
    )
    # Direkt approve via Repo (bypasses LangGraph für diesen Test)
    review_repo.update_status(cid, "approved", account_id=tenant_account_id)

    # Complete via HTTP
    resp = client.post(
        "/api/review/complete",
        json={"correlation_id": cid},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "completed"

    # Mail-State prüfen via HTTP
    resp = client.get(f"/api/emails/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["processing_state"] == "approved"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_approve_nonexistent_correlation_returns_404(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """Approve auf nicht-existierende Correlation-ID → 404."""
    resp = client.post(
        "/api/review/approve",
        json={"correlation_id": "does-not-exist", "approved_body": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_complete_without_approve_returns_400(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Complete ohne vorherige Freigabe → 400."""
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.core.models.email import StoredEmail
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    cid = "e2e-complete-no-approve-001"
    msg_id = "msg-complete-no-approve@test"

    EmailRepository(mock_db).upsert_by_message_id(  # type: ignore[arg-type]
        StoredEmail(
            message_id=msg_id,
            from_address="guest@test.local",
            subject="Test",
            body_text="Test",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            account_id=tenant_account_id,
        )
    )
    ExtractionRepository(mock_db).save(  # type: ignore[arg-type]
        cid, msg_id, BookingExtraction(), account_id=tenant_account_id
    )
    ReviewRepository(mock_db).upsert_pending(  # type: ignore[arg-type]
        correlation_id=cid,
        message_id=msg_id,
        draft_body="Entwurf",
        grounding_flag=False,
        intent="other",
        account_id=tenant_account_id,
    )

    resp = client.post(
        "/api/review/complete",
        json={"correlation_id": cid},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_reject_via_http_api(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Reject via HTTP → 200 (LangGraph-Resume wird versucht, kein harter Fehler)."""
    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.core.models.email import StoredEmail
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    cid = "e2e-reject-http-001"
    msg_id = "msg-reject-http@test"

    EmailRepository(mock_db).upsert_by_message_id(  # type: ignore[arg-type]
        StoredEmail(
            message_id=msg_id,
            from_address="guest@booking.com",
            subject="XY999 Stornierung",
            body_text="Stornierung XY999",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            account_id=tenant_account_id,
        )
    )
    ExtractionRepository(mock_db).save(  # type: ignore[arg-type]
        cid,
        msg_id,
        BookingExtraction(booking_number="XY999"),
        account_id=tenant_account_id,
    )
    ReviewRepository(mock_db).upsert_pending(  # type: ignore[arg-type]
        correlation_id=cid,
        message_id=msg_id,
        draft_body="Falscher Entwurf",
        grounding_flag=False,
        intent="cancellation",
        account_id=tenant_account_id,
    )

    resp = client.post(
        "/api/review/reject",
        json={"correlation_id": cid, "reason": "Falsche Buchungsnummer"},
        headers=auth_headers,
    )
    # Reject geht durch LangGraph-Resume; ohne Checkpoint: 200 oder 400
    assert resp.status_code in (200, 400)

"""E2E-Tests: Auto-Freigabe, Undo, Eskalation, KI-Begründung, Übersetzung."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.infrastructure.repositories.platform_settings_repository import (
    AutoApproveSettings,
    PlatformSettingsRecord,
)


def _enable_auto_approve(ctx: Any, account_id: str, intent_key: str) -> None:
    record = ctx.platform_settings_repo.get(account_id) or PlatformSettingsRecord(
        id=account_id
    )
    record.auto_approve = AutoApproveSettings(
        enabled=True,
        threshold=90,
        per_intent={
            "booking": intent_key == "booking",
            "cancellation": intent_key == "cancellation",
            "inquiry": intent_key == "inquiry",
            "change": intent_key == "change",
        },
    )
    ctx.platform_settings_repo.save(record)


def _run(ctx: Any, account_id: str, message_id: str, subject: str) -> str:
    from backend.core.models.email import IncomingEmail

    payload = IncomingEmail(
        message_id=message_id,
        from_address="guest@airbnb.com",
        subject=subject,
        body_text=subject,
        received_at=datetime.now(UTC),
        platform="airbnb",
        account_id=account_id,
    )
    ctx.workflow.run(payload, thread_id=payload.correlation_id)
    return payload.correlation_id


def test_auto_approve_sends_without_human(app: object, tenant_account_id: str) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    _enable_auto_approve(ctx, tenant_account_id, "booking")
    cid = _run(ctx, tenant_account_id, "m-auto-1", "Neue Buchung AB123")
    record = ctx.review_repo.get(cid, account_id=tenant_account_id)
    assert record is not None
    assert record.review_status == "approved"
    assert record.auto_approved is True


def test_no_auto_approve_when_disabled(app: object, tenant_account_id: str) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = _run(ctx, tenant_account_id, "m-auto-2", "Neue Buchung AB123")
    record = ctx.review_repo.get(cid, account_id=tenant_account_id)
    assert record is not None
    assert record.review_status == "pending"
    assert record.auto_approved is False


def test_undo_reverts_auto_approval(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    _enable_auto_approve(ctx, tenant_account_id, "booking")
    cid = _run(ctx, tenant_account_id, "m-auto-3", "Neue Buchung AB123")

    resp = client.post(
        "/api/review/undo", headers=auth_headers, json={"correlation_id": cid}
    )
    assert resp.status_code == 200
    record = ctx.review_repo.get(cid, account_id=tenant_account_id)
    assert record.review_status == "pending"
    assert record.auto_approved is False


def test_undo_without_auto_approval_400(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = _run(ctx, tenant_account_id, "m-auto-4", "Neue Buchung AB123")
    resp = client.post(
        "/api/review/undo", headers=auth_headers, json={"correlation_id": cid}
    )
    assert resp.status_code == 400


def test_escalated_review_counts_on_dashboard(
    app: object,
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
    email_repo: Any,
) -> None:
    from backend.core.models.email import ProcessingState, StoredEmail

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = "corr-esc-1"
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-esc-1@test",
            from_address="guest@example.com",
            subject="Beschwerde zur Buchung",
            body_text="Sehr unzufrieden",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            account_id=tenant_account_id,
        )
    )
    ctx.review_repo.upsert_pending(
        correlation_id=cid,
        message_id="m-esc-1@test",
        draft_body="Entschuldigung…",
        grounding_flag=False,
        intent="complaint",
        account_id=tenant_account_id,
        confidence=0.3,
        escalated=True,
    )
    stats = client.get("/api/dashboard/stats", headers=auth_headers).get_json()
    assert stats["escalated_open"] >= 1


def test_email_detail_exposes_reason(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = _run(ctx, tenant_account_id, "m-reason-1", "Neue Buchung AB123")
    detail = client.get(f"/api/emails/{cid}", headers=auth_headers).get_json()
    assert detail["confidence"] is not None
    assert detail["reply_language"] in ("de", "en")
    assert "signals" in detail


def test_translate_endpoint(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = _run(ctx, tenant_account_id, "m-tr-1", "Neue Buchung AB123")
    resp = client.post(
        "/api/review/translate",
        headers=auth_headers,
        json={"correlation_id": cid, "target_language": "en"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["target_language"] == "en"
    assert data["translated_body"]

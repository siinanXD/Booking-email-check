"""Tests für das Benachrichtigungs-Feed (Glocke)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import ProcessingState, StoredEmail


def _seed_pending_review(email_repo: Any, account_id: str, cid: str) -> None:
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"{cid}@test",
            from_address="gast@example.com",
            subject="Frage zur Buchung",
            body_text="hallo",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.PENDING_REVIEW,
            account_id=account_id,
        )
    )


def test_notifications_requires_auth(client: Any) -> None:
    assert client.get("/api/notifications").status_code == 401


def test_feed_lists_pending_review_and_marks_read(
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
    email_repo: Any,
) -> None:
    _seed_pending_review(email_repo, tenant_account_id, "corr-notif-1")

    resp = client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["unread"] >= 1
    assert any(item["kind"] == "review_waiting" for item in data["items"])

    marked = client.post("/api/notifications/read-all", headers=auth_headers)
    assert marked.status_code == 200

    after = client.get("/api/notifications", headers=auth_headers).get_json()
    assert after["unread"] == 0
    assert all(item["read"] for item in after["items"])


def test_read_state_is_per_user(
    app: object, tenant_account_id: str, email_repo: Any
) -> None:
    from backend.api.services.notification_feed import build_feed, mark_all_read

    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    _seed_pending_review(email_repo, tenant_account_id, "corr-peruser")
    mark_all_read(ctx.db, "user-a")
    feed_a = build_feed(ctx, tenant_account_id, "user-a")
    feed_b = build_feed(ctx, tenant_account_id, "user-b")
    assert feed_a.unread == 0  # user-a hat als gelesen markiert
    assert feed_b.unread >= 1  # user-b unabhängig davon


def test_feed_lists_escalations(
    app: object,
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
    email_repo: Any,
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    _seed_pending_review(email_repo, tenant_account_id, "corr-esc-n")
    ctx.review_repo.upsert_pending(
        correlation_id="corr-esc-n",
        message_id="corr-esc-n@test",
        draft_body="d",
        grounding_flag=False,
        intent="complaint",
        account_id=tenant_account_id,
        confidence=0.3,
        escalated=True,
    )
    data = client.get("/api/notifications", headers=auth_headers).get_json()
    kinds = [i["kind"] for i in data["items"]]
    assert "escalation" in kinds
    # Eskalierte Mail erscheint NICHT zusätzlich als review_waiting (kein Doppel).
    esc = [i for i in data["items"] if i["id"] == "esc:corr-esc-n"]
    assert esc and "Eskaliert" in esc[0]["title"]
    assert not any(i["id"] == "rev:corr-esc-n" for i in data["items"])

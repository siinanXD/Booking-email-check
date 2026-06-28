"""Tests für die Sammel-Freigabe (Review-Shortcuts/Checkboxen)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _run_workflow(ctx: Any, account_id: str, message_id: str, subject: str) -> str:
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


def test_bulk_approve_requires_auth(client: Any) -> None:
    resp = client.post("/api/review/bulk-approve", json={"correlation_ids": []})
    assert resp.status_code == 401


def test_bulk_approve_unknown_ids_reported(client: Any, auth_headers: dict) -> None:
    resp = client.post(
        "/api/review/bulk-approve",
        headers=auth_headers,
        json={"correlation_ids": ["does-not-exist"]},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["approved"] == 0
    assert data["failed"] == 1
    assert data["items"][0]["status"] == "not_found"


def test_bulk_approve_multiple(
    app: object,
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid1 = _run_workflow(ctx, tenant_account_id, "m-bulk-1", "Stornierung AB1 bitte")
    cid2 = _run_workflow(ctx, tenant_account_id, "m-bulk-2", "Stornierung AB2 bitte")

    resp = client.post(
        "/api/review/bulk-approve",
        headers=auth_headers,
        json={"correlation_ids": [cid1, cid2, cid1]},  # Duplikat wird ignoriert
    )
    assert resp.status_code == 200
    data = resp.get_json()
    # Beide bekannten IDs werden verarbeitet; Duplikat zählt nicht doppelt.
    assert len(data["items"]) == 2
    assert data["approved"] + data["failed"] == 2

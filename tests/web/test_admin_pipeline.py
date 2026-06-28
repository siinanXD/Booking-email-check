"""Admin-Datenfluss-Board: Funnel/Entscheidungen, Status, Stuck, Trace."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import ProcessingState, StoredEmail


def _ctx(app: object) -> Any:
    return app.extensions["ctx"]  # type: ignore[union-attr]


def _seed_mail(ctx: Any, account_id: str, cid: str, state: ProcessingState) -> None:
    ctx.email_repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"{cid}@t",
            from_address="gast@example.com",
            subject=f"Mail {cid}",
            body_text="x",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=state,
            account_id=account_id,
        )
    )


# ── Pipeline (Funnel + Entscheidungen) ──────────────────────────────────────


def test_pipeline_requires_platform_admin(
    client: Any, tenant_owner_auth_headers: dict
) -> None:
    resp = client.get("/api/admin/pipeline", headers=tenant_owner_auth_headers)
    assert resp.status_code == 403


def test_pipeline_empty_has_all_states(client: Any, auth_headers: dict) -> None:
    data = client.get("/api/admin/pipeline", headers=auth_headers).get_json()
    states = {s["state"] for s in data["funnel"]["states"]}
    assert states == {s.value for s in ProcessingState}
    assert data["funnel"]["total"] == 0


def test_pipeline_counts_and_decisions(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = _ctx(app)
    _seed_mail(ctx, tenant_account_id, "p1", ProcessingState.RECEIVED)
    _seed_mail(ctx, tenant_account_id, "p2", ProcessingState.DRAFTED)
    _seed_mail(ctx, tenant_account_id, "p3", ProcessingState.DRAFTED)
    ctx.review_repo.upsert_pending(
        correlation_id="p2",
        message_id="p2@t",
        draft_body="d",
        grounding_flag=True,
        intent="complaint",
        account_id=tenant_account_id,
        confidence=0.3,
        escalated=True,
        source_flags=["Zimmer widersprüchlich: Betreff Nr. 3 vs. Mailtext Nr. 1"],
    )
    data = client.get("/api/admin/pipeline?days=365", headers=auth_headers).get_json()
    by_state = {s["state"]: s["count"] for s in data["funnel"]["states"]}
    assert by_state["drafted"] == 2
    assert by_state["received"] == 1
    dec = data["decisions"]
    assert dec["escalated"] == 1
    assert dec["pending"] == 1
    assert dec["grounding"]["fail"] == 1
    assert dec["top_source_flags"][0]["flag"] == "Zimmer widersprüchlich"


# ── Status-Ampel ────────────────────────────────────────────────────────────


def test_status_smoke(client: Any, auth_headers: dict) -> None:
    data = client.get("/api/admin/status", headers=auth_headers).get_json()
    assert data["db"]["ok"] is True
    assert data["integrations"]["langfuse_configured"] is True
    assert data["integrations"]["sentry_configured"] is False
    assert data["overall"] in ("ok", "degraded", "down")
    assert set(data["whatsapp_24h"]) == {"sent", "failed", "skipped", "pending"}


def test_status_requires_platform_admin(
    client: Any, tenant_owner_auth_headers: dict
) -> None:
    resp = client.get("/api/admin/status", headers=tenant_owner_auth_headers)
    assert resp.status_code == 403


# ── Stuck-Liste ─────────────────────────────────────────────────────────────


def test_stuck_processing_respects_age(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = _ctx(app)
    _seed_mail(ctx, tenant_account_id, "stuck-old", ProcessingState.DRAFTED)
    ctx.db["emails"].update_one(
        {"_id": "stuck-old@t"},
        {"$set": {"updated_at": "2001-01-01T00:00:00+00:00"}},
    )
    _seed_mail(ctx, tenant_account_id, "stuck-fresh", ProcessingState.DRAFTED)
    data = client.get("/api/admin/mails/stuck?hours=1", headers=auth_headers).get_json()
    cids = [i["correlation_id"] for i in data["items"]]
    assert "stuck-old" in cids
    assert "stuck-fresh" not in cids
    assert data["kind"] == "processing"


def test_stuck_discarded(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = _ctx(app)
    _seed_mail(ctx, tenant_account_id, "disc-1", ProcessingState.DISCARDED)
    data = client.get(
        "/api/admin/mails/stuck?kind=discarded", headers=auth_headers
    ).get_json()
    assert data["kind"] == "discarded"
    assert any(i["correlation_id"] == "disc-1" for i in data["items"])


# ── Einzel-Trace ────────────────────────────────────────────────────────────


def test_trace_enriched_and_404(
    app: object, client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    ctx = _ctx(app)
    _seed_mail(ctx, tenant_account_id, "tr-1", ProcessingState.PENDING_REVIEW)
    ctx.review_repo.upsert_pending(
        correlation_id="tr-1",
        message_id="tr-1@t",
        draft_body="d",
        grounding_flag=False,
        intent="new_booking",
        account_id=tenant_account_id,
        confidence=0.92,
    )
    base = f"/api/admin/accounts/{tenant_account_id}/mails"
    data = client.get(f"{base}/tr-1/trace", headers=auth_headers).get_json()
    review_events = [e for e in data["events"] if e["kind"].startswith("review_")]
    assert review_events and review_events[0]["confidence"] == 0.92
    assert review_events[0]["intent"] == "new_booking"

    missing = client.get(f"{base}/does-not-exist/trace", headers=auth_headers)
    assert missing.status_code == 404


def test_trace_requires_platform_admin(
    client: Any, tenant_owner_auth_headers: dict, tenant_account_id: str
) -> None:
    resp = client.get(
        f"/api/admin/accounts/{tenant_account_id}/mails/x/trace",
        headers=tenant_owner_auth_headers,
    )
    assert resp.status_code == 403

"""Aggregationen fürs Admin-Datenfluss-Board (mongomock)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.review_repository import ReviewRepository

_SINCE = "2000-01-01T00:00:00+00:00"
_FUTURE = "2999-01-01T00:00:00+00:00"


def _seed_mail(email_repo: Any, cid: str, state: ProcessingState) -> None:
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"{cid}@t",
            from_address="a@b.com",
            subject=f"Mail {cid}",
            body_text="x",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=state,
            account_id="acc-1",
        )
    )


def test_count_by_all_states(email_repo: Any) -> None:
    _seed_mail(email_repo, "c1", ProcessingState.DRAFTED)
    _seed_mail(email_repo, "c2", ProcessingState.DRAFTED)
    _seed_mail(email_repo, "c3", ProcessingState.APPROVED)
    _seed_mail(email_repo, "c4", ProcessingState.DISCARDED)
    counts = email_repo.count_by_all_states(_SINCE)
    assert counts["drafted"] == 2
    assert counts["approved"] == 1
    assert counts["discarded"] == 1


def test_list_stuck_respects_age(email_repo: Any, mock_db: Any) -> None:
    _seed_mail(email_repo, "old", ProcessingState.DRAFTED)
    mock_db["emails"].update_one(
        {"_id": "old@t"}, {"$set": {"updated_at": "2001-01-01T00:00:00+00:00"}}
    )
    _seed_mail(email_repo, "fresh", ProcessingState.DRAFTED)
    stuck = email_repo.list_stuck(["drafted"], "2002-01-01T00:00:00+00:00")
    assert [m.correlation_id for m in stuck] == ["old"]
    assert email_repo.list_stuck(["drafted"], _SINCE) == []


def test_decision_breakdown(mock_db: Any) -> None:
    repo = ReviewRepository(mock_db)
    repo.upsert_pending(
        correlation_id="r1",
        message_id="r1@t",
        draft_body="d",
        grounding_flag=False,
        intent="new_booking",
        account_id="acc-1",
        confidence=0.95,
    )
    repo.upsert_pending(
        correlation_id="r2",
        message_id="r2@t",
        draft_body="d",
        grounding_flag=True,
        intent="complaint",
        account_id="acc-1",
        confidence=0.30,
        escalated=True,
        source_flags=["Zimmer widersprüchlich: Betreff Nr. 3 vs. Mailtext Nr. 1"],
    )
    repo.upsert_pending(
        correlation_id="r3",
        message_id="r3@t",
        draft_body="d",
        grounding_flag=False,
        intent="new_booking",
        account_id="acc-1",
        confidence=0.99,
    )
    repo.update_status(
        "r3", "approved", account_id="acc-1", extra_fields={"auto_approved": True}
    )

    b = repo.decision_breakdown(_SINCE)
    assert b["auto_approved"] == 1
    assert b["pending"] == 2
    assert b["escalated"] == 1
    assert b["grounding"]["fail"] == 1
    # Konfidenz-Buckets: 0.30 → 0–50%, 0.95/0.99 → 90–100%.
    by_bucket = {x["bucket"]: x["count"] for x in b["confidence_buckets"]}
    assert by_bucket["0–50%"] == 1
    assert by_bucket["90–100%"] == 2
    assert b["top_source_flags"][0]["flag"] == "Zimmer widersprüchlich"

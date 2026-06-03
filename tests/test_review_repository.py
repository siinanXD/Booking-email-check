"""Tests für ReviewRepository."""

from __future__ import annotations

from backend.core.models.response import ReviewStatus
from backend.infrastructure.repositories.review_repository import ReviewRepository


def test_upsert_pending_and_list(mock_db) -> None:
    """Pending Review wird persistiert und gelistet."""
    repo = ReviewRepository(mock_db)
    repo.upsert_pending(
        correlation_id="corr-pending",
        message_id="msg-1",
        draft_body="Draft text",
        grounding_flag=False,
        intent="guest_inquiry",
    )
    pending = repo.list_pending()
    assert len(pending) == 1
    assert pending[0].correlation_id == "corr-pending"
    assert pending[0].review_status == "pending"


def test_mark_approved_persists(mock_db) -> None:
    """Freigabe aktualisiert Status und approved_body."""
    repo = ReviewRepository(mock_db)
    repo.upsert_pending(
        correlation_id="corr-approve",
        message_id="msg-2",
        draft_body="Draft",
        grounding_flag=False,
        intent=None,
    )
    updated = repo.mark_approved("corr-approve", "Final body")
    assert updated is not None
    assert updated.review_status == "approved"
    assert updated.approved_body == "Final body"
    assert repo.list_pending() == []


def test_mark_rejected_persists(mock_db) -> None:
    """Ablehnung aktualisiert Status und reviewer_note."""
    repo = ReviewRepository(mock_db)
    repo.upsert_pending(
        correlation_id="corr-reject",
        message_id="msg-3",
        draft_body="Draft",
        grounding_flag=True,
        intent=None,
    )
    updated = repo.mark_rejected("corr-reject", "Not accurate")
    assert updated is not None
    assert updated.review_status == "rejected"
    assert updated.reviewer_note == "Not accurate"


def test_save_alias_and_survives_repo_recreate(mock_db) -> None:
    """save/get_by_correlation_id Alias; Daten überleben Neustart."""
    repo = ReviewRepository(mock_db)
    review = ReviewStatus(correlation_id="corr-save", status="pending")
    repo.save(
        review,
        message_id="msg-4",
        draft_body="Saved draft",
        grounding_flag=False,
    )
    repo2 = ReviewRepository(mock_db)
    loaded = repo2.get_by_correlation_id("corr-save")
    assert loaded is not None
    assert loaded.status == "pending"
    statuses = repo2.list_pending_statuses()
    assert any(item.correlation_id == "corr-save" for item in statuses)

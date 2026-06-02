"""Tests für EmailRepository."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import ProcessingState, StoredEmail


def test_upsert_and_get(email_repo) -> None:
    email = StoredEmail(
        message_id="repo-test-1",
        from_address="a@b.com",
        subject="Test",
        body_text="Hi",
        received_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(email)
    loaded = email_repo.get_by_message_id("repo-test-1")
    assert loaded is not None
    assert loaded.subject == "Test"


def test_update_processing_state(email_repo) -> None:
    email = StoredEmail(
        message_id="repo-test-2",
        from_address="a@b.com",
        body_text="x",
        received_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(email)
    updated = email_repo.update_processing_state(
        "repo-test-2",
        ProcessingState.TRIAGED,
    )
    assert updated is not None
    assert updated.processing_state == ProcessingState.TRIAGED

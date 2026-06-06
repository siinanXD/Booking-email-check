"""Tests für EmailRepository."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.models.email import ProcessingState, StoredEmail


def test_upsert_and_get(email_repo) -> None:
    """Verify upsert and get."""
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
    """Verify update processing state."""
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


def test_find_existing_message_ids_batch(email_repo) -> None:
    """Batch-Dedup liefert nur bereits gespeicherte IDs."""
    for mid in ("batch-a", "batch-b"):
        email_repo.upsert_by_message_id(
            StoredEmail(
                message_id=mid,
                from_address="a@b.com",
                body_text="x",
                received_at=datetime.now(UTC),
            )
        )
    found = email_repo.find_existing_message_ids(
        ["batch-a", "batch-b", "batch-c"],
    )
    assert found == {"batch-a", "batch-b"}

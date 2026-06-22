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


def test_update_processing_state_persists_relevance(email_repo) -> None:
    """update_processing_state schreibt is_booking/effective_intent via **extra."""
    email = StoredEmail(
        message_id="repo-rel-1",
        from_address="bookings@beds24.com",
        subject="Storno: 12345",
        body_text="x",
        received_at=datetime.now(UTC),
        correlation_id="corr-rel-1",
        account_id="acc-1",
    )
    email_repo.upsert_by_message_id(email)
    email_repo.update_processing_state(
        "repo-rel-1",
        ProcessingState.EXTRACTED,
        account_id="acc-1",
        is_booking=True,
        effective_intent="cancellation",
    )
    loaded = email_repo.get_by_message_id("repo-rel-1", account_id="acc-1")
    assert loaded is not None
    assert loaded.is_booking is True
    assert loaded.effective_intent == "cancellation"


def test_list_filtered_booking_related_uses_stored_fields(email_repo) -> None:
    """Booking-Pfad filtert DB-seitig über is_booking + effective_intent."""
    base = dict(from_address="a@b.com", body_text="x", account_id="acc-1")
    # Treffer: Buchung mit passendem Intent
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="b-hit",
            subject="Storno",
            received_at=datetime.now(UTC),
            correlation_id="c-hit",
            is_booking=True,
            effective_intent="cancellation",
            **base,
        )
    )
    # Kein Treffer: Nicht-Buchung
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="b-noise",
            subject="Newsletter",
            received_at=datetime.now(UTC),
            correlation_id="c-noise",
            is_booking=False,
            effective_intent=None,
            **base,
        )
    )
    # Kein Treffer: noch nicht klassifiziert
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="b-unknown",
            subject="Pending",
            received_at=datetime.now(UTC),
            correlation_id="c-unknown",
            **base,
        )
    )
    items, total = email_repo.list_filtered(
        account_id="acc-1",
        booking_related=True,
        intents=["cancellation"],
    )
    assert total == 1
    assert [e.message_id for e in items] == ["b-hit"]


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

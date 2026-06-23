"""Routing-Gates des Email-Workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.workflows import routing
from backend.core.models.email import StoredEmail


def _email() -> StoredEmail:
    return StoredEmail(
        message_id="m1",
        from_address="news@example.com",
        subject="Newsletter",
        body_text="Bitte hier abmelden.",
        received_at=datetime.now(UTC),
        correlation_id="c1",
        account_id="a1",
    )


def test_after_classify_skips_extraction_for_clear_non_booking(monkeypatch) -> None:
    """intent=OTHER ohne Rettungssignale → verwerfen, keine Extraktion."""
    monkeypatch.setattr(routing, "has_reservation_request_signals", lambda e: False)
    monkeypatch.setattr(routing, "is_probable_booking_mail", lambda e: False)
    monkeypatch.setattr(routing, "infer_beds24_intent", lambda s: None)
    repo = MagicMock()
    state = {"email": _email(), "intent": BookingIntent.OTHER}
    assert routing.after_classify(state, email_repo=repo) == "end"
    repo.update_processing_state.assert_called_once()
    assert (
        repo.update_processing_state.call_args.kwargs.get("triage_outcome")
        == "not_booking_pre_extract"
    )


def test_after_classify_extracts_informal_booking(monkeypatch) -> None:
    """intent=OTHER + Reservierungssignal → extrahieren (enrich rettet später)."""
    monkeypatch.setattr(routing, "has_reservation_request_signals", lambda e: True)
    monkeypatch.setattr(routing, "is_probable_booking_mail", lambda e: False)
    monkeypatch.setattr(routing, "infer_beds24_intent", lambda s: None)
    repo = MagicMock()
    state = {"email": _email(), "intent": BookingIntent.OTHER}
    assert routing.after_classify(state, email_repo=repo) == "extract"
    repo.update_processing_state.assert_not_called()


def test_after_classify_extracts_booking_intent() -> None:
    repo = MagicMock()
    state = {"email": _email(), "intent": BookingIntent.NEW_BOOKING}
    assert routing.after_classify(state, email_repo=repo) == "extract"
    repo.update_processing_state.assert_not_called()


def test_after_classify_extracts_tenant_workflow() -> None:
    repo = MagicMock()
    state = {"email": _email(), "intent": BookingIntent.OTHER, "workflow_id": "wf1"}
    assert routing.after_classify(state, email_repo=repo) == "extract"
    repo.update_processing_state.assert_not_called()

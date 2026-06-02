"""Tests für regelbasierte Triage."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import IncomingEmail
from schemas.booking.triage import TriageOutcome
from services.triage import TriageService


def test_triage_relevant_booking() -> None:
    email = IncomingEmail(
        message_id="m1",
        from_address="guest@airbnb.com",
        subject="Buchung",
        body_text="Neue Reservierung",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    result = TriageService().triage(email)
    assert result.outcome == TriageOutcome.RELEVANT


def test_triage_phishing() -> None:
    email = IncomingEmail(
        message_id="m2",
        from_address="x@evil.com",
        subject="Urgent",
        body_text="Click here immediately verify your account",
        received_at=datetime.now(UTC),
    )
    result = TriageService().triage(email)
    assert result.outcome == TriageOutcome.SPAM_PHISHING


def test_triage_empty_noreply() -> None:
    email = IncomingEmail(
        message_id="m3",
        from_address="noreply@mailer-daemon.local",
        subject="",
        body_text="",
        received_at=datetime.now(UTC),
    )
    result = TriageService().triage(email)
    assert result.outcome == TriageOutcome.SPAM_PHISHING

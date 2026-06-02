"""Tests für regelbasierte Triage."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.domain.booking.triage import TriageOutcome
from backend.ai.services.triage import TriageService
from backend.core.models.email import IncomingEmail


def test_triage_relevant_booking() -> None:
    """Verify triage relevant booking."""
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
    """Verify triage phishing."""
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
    """Verify triage empty noreply."""
    email = IncomingEmail(
        message_id="m3",
        from_address="noreply@mailer-daemon.local",
        subject="",
        body_text="",
        received_at=datetime.now(UTC),
    )
    result = TriageService().triage(email)
    assert result.outcome == TriageOutcome.SPAM_PHISHING


def test_triage_unknown_domain_ignores_platform_hint() -> None:
    """Platform-Hint darf unbekannte Absender-Domain nicht überstimmen."""
    email = IncomingEmail(
        message_id="m4",
        from_address="unknown@random.org",
        subject="Hello",
        body_text="Generic inquiry",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    result = TriageService().triage(email)
    assert result.outcome == TriageOutcome.UNKNOWN_DOMAIN

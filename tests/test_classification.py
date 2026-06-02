"""Tests für Klassifikation mit Mock-LLM."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import StoredEmail
from schemas.booking.taxonomy import BookingIntent
from services.classification import ClassificationService
from tests.mocks import MockLLM


def test_classify_mock() -> None:
    email = StoredEmail(
        message_id="c1",
        from_address="g@airbnb.com",
        subject="Stornierung AB1",
        body_text="Bitte stornieren",
        received_at=datetime.now(UTC),
    )
    svc = ClassificationService(MockLLM(), "gpt-4o-mini")
    assert svc.classify(email) == BookingIntent.CANCELLATION

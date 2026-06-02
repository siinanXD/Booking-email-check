"""Tests für Extraktion."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import StoredEmail
from schemas.booking.taxonomy import BookingIntent
from services.extraction import ExtractionService
from tests.mocks import MockLLM


def test_extract_parses_booking_number() -> None:
    email = StoredEmail(
        message_id="ext-1",
        from_address="g@airbnb.com",
        subject="Buchung AB123",
        body_text="Reservierung AB123",
        received_at=datetime.now(UTC),
    )
    ext = ExtractionService(MockLLM(), "gpt-4o-mini").extract(
        email,
        intent=BookingIntent.NEW_BOOKING,
    )
    assert ext.booking_number == "AB123"
    assert ext.check_in is not None

"""Tests für Validierung."""

from __future__ import annotations

from datetime import date

from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from services.validation import ValidationService


def test_validate_dates_ok() -> None:
    ext = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        check_in=date(2026, 6, 12),
        check_out=date(2026, 6, 15),
    )
    result = ValidationService().validate(ext)
    assert result.valid is True


def test_validate_dates_invalid() -> None:
    ext = BookingExtraction(
        check_in=date(2026, 6, 15),
        check_out=date(2026, 6, 12),
    )
    result = ValidationService().validate(ext)
    assert result.valid is False


def test_validate_cancellation_requires_booking_number() -> None:
    ext = BookingExtraction(intent=BookingIntent.CANCELLATION)
    result = ValidationService().validate(ext)
    assert result.valid is False

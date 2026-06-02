"""Tests für Buchungs-Mail-Erkennung."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import StoredEmail
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from services.booking_relevance import (
    classify_booking_mail,
    is_booking_relevant,
    is_marketing_noise,
    is_probable_booking_mail,
    is_probable_non_booking_mail,
)


def test_comigo_newsletter_not_relevant() -> None:
    email = StoredEmail(
        message_id="m1",
        from_address="info@comigo.de",
        subject="Comigo Info at Lumigita",
        body_text="Monatlicher Newsletter",
        received_at=datetime.now(UTC),
        correlation_id="c1",
    )
    ext = BookingExtraction(intent=BookingIntent.CANCELLATION)
    assert is_marketing_noise(email)
    assert not is_booking_relevant(email, ext)


def test_temu_not_booking() -> None:
    email = StoredEmail(
        message_id="m-temu",
        from_address="noreply@temu.com",
        subject="Deine Temu-Bestellung wurde zugestellt",
        body_text="Paket",
        received_at=datetime.now(UTC),
        correlation_id="c-temu",
    )
    assert is_probable_non_booking_mail(email)
    assert not classify_booking_mail(
        email,
        BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="AB200"),
    ).is_booking


def test_beds24_booking_detected() -> None:
    email = StoredEmail(
        message_id="m2",
        from_address="bookings@beds24.com",
        subject="Buchung: Münzbach Ferienzimmer",
        body_text="Reservierung",
        received_at=datetime.now(UTC),
        correlation_id="c2",
        platform="beds24",
    )
    assert is_probable_booking_mail(email)
    ext = BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="86972494")
    assert classify_booking_mail(email, ext).is_booking


def test_cancellation_with_booking_number_relevant() -> None:
    email = StoredEmail(
        message_id="m3",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Bitte stornieren",
        received_at=datetime.now(UTC),
        correlation_id="c3",
        platform="airbnb",
    )
    ext = BookingExtraction(
        intent=BookingIntent.CANCELLATION,
        booking_number="AB200",
    )
    assert is_booking_relevant(email, ext)

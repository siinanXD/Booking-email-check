"""Tests für Buchungs-Mail-Erkennung."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.domain.booking.booking_relevance import (
    classify_booking_mail,
    effective_booking_intent,
    has_booking_rescue_signals,
    has_reservation_request_signals,
    has_text_booking_signals,
    is_booking_relevant,
    is_marketing_noise,
    is_probable_booking_mail,
    is_probable_non_booking_mail,
)
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import StoredEmail


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


def test_endclothing_newsletter_not_booking_even_if_llm_new_booking() -> None:
    """Fashion-Newsletter darf nicht als Buchung zählen (LLM-Fehler abfangen)."""
    email = StoredEmail(
        message_id="m-end",
        from_address="news@info.endclothing.com",
        subject="New arrivals — up to 50% off",
        body_text="Shop the latest sale at END.",
        received_at=datetime.now(UTC),
        correlation_id="c-end",
    )
    ext = BookingExtraction(intent=BookingIntent.NEW_BOOKING)
    assert is_marketing_noise(email)
    assert not classify_booking_mail(email, ext).is_booking
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


def test_gmail_reservation_keywords() -> None:
    email = StoredEmail(
        message_id="m-gmail",
        from_address="guest@gmail.com",
        subject="Frage zur Reservierung",
        body_text="Wann kann ich einchecken?",
        received_at=datetime.now(UTC),
        correlation_id="c-gmail",
    )
    assert has_text_booking_signals(email)
    assert is_probable_booking_mail(email)


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


def test_informal_booking_request_with_llm_intent() -> None:
    email = StoredEmail(
        message_id="m-informal",
        from_address="max@example.com",
        subject="Anfrage",
        body_text="Name: Max Mustermann\nich würde gerne diese Buchung tätigen",
        received_at=datetime.now(UTC),
        correlation_id="c-informal",
    )
    assert has_reservation_request_signals(email)
    ext = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING, guest_name="Max Mustermann"
    )
    verdict = classify_booking_mail(email, ext)
    assert verdict.is_booking
    assert verdict.reason == "llm_new_booking"
    assert effective_booking_intent(email, ext) == BookingIntent.NEW_BOOKING


def test_reservation_request_without_extraction() -> None:
    email = StoredEmail(
        message_id="m-no-ext",
        from_address="guest@gmail.com",
        subject="Zimmer",
        body_text="I would like to book a room for next week",
        received_at=datetime.now(UTC),
        correlation_id="c-no-ext",
    )
    verdict = classify_booking_mail(email, None)
    assert verdict.is_booking
    assert verdict.reason == "reservation_request_heuristic"


def test_rescue_signals_pms_subject() -> None:
    """PMS-Betreff rettet eine LLM-Klassifikation als OTHER."""
    email = StoredEmail(
        message_id="m-rescue",
        from_address="office@hotel.example",
        subject="Stornierung: 12345",
        body_text="",
        received_at=datetime.now(UTC),
        correlation_id="c-rescue",
    )
    assert has_booking_rescue_signals(email)


def test_rescue_signals_absent_for_plain_mail() -> None:
    email = StoredEmail(
        message_id="m-plain",
        from_address="someone@example.org",
        subject="Hallo",
        body_text="Allgemeine Frage zu Ihrem Unternehmen.",
        received_at=datetime.now(UTC),
        correlation_id="c-plain",
    )
    assert not has_booking_rescue_signals(email)

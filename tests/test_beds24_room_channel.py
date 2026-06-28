"""Deterministische Zimmer-/Kanal-Extraktion aus beds24-Mails (Ticket 1).

Eval/Regression gegen die vier Buchungen aus dem Ticket. Yue Dai ist der
verbatim-Mailtext aus dem Ticket; die übrigen Bodys folgen demselben
beds24-Template mit den belegten Wahrheitswerten (Pulse-App).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.ai.domain.booking.beds24_fields import (
    detect_channel,
    expects_room,
    parse_room_number,
)
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.extraction_enrichment import enrich_extraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.features.notifications.notification_template_payload import (
    _property_display,
)

YUE_DAI_BODY = (
    "Neue Buchungsbenachrichtigung.\n\n"
    "Münzbach Ferienzimmer\n\n"
    "Zimmer Nr. 3\n"
    "Buchungsnummer: 88902627\n"
    "Personen 2\n"
    "Preis €345.46\n\n"
    "Check-in Mi 9 Sep 2026\n"
    "Letzte Übernachtung Fr 11 Sep 2026\n"
    "Check-out Sa 12 Sep 2026\n\n"
    "Booking.com 5628649148\n\n"
    "Name Yue Dai\n"
    "Email: ydai_543285@guest.booking.com\n"
)


def _beds24_body(property_name: str, room_line: str, guest_email: str) -> str:
    return (
        f"Neue Buchungsbenachrichtigung.\n\n{property_name}\n\n"
        f"{room_line}"
        "Buchungsnummer: 99999999\nPersonen 2\n\n"
        "Check-in Mo 1 Jan 2026\nCheck-out Mi 3 Jan 2026\n\n"
        f"Booking.com 5000000000\n\nName Test Gast\nEmail: {guest_email}\n"
    )


def _email(subject: str, body: str) -> StoredEmail:
    return StoredEmail(
        message_id="m@test",
        from_address="bookings@beds24.com",
        subject=subject,
        body_text=body,
        received_at=datetime.now(UTC),
        correlation_id="corr-x",
        processing_state=ProcessingState.CLASSIFIED,
        account_id="acc-1",
    )


# --- Parser-Einheiten -------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Zimmer Nr. 3", "3"),
        ("Zimmer Nr.1", "1"),
        ("zimmer nr 12", "12"),
        ("Zimmer Nummer 2", "2"),
        ("Münzbach Ferienzimmer", None),  # 'Ferienzimmer' ohne 'Nr' → kein Treffer
        ("Apartment mit 2 Schlafzimmern und Balkon", None),
    ],
)
def test_parse_room_number(text: str, expected: str | None) -> None:
    assert parse_room_number(text) == expected


def test_channel_domain_beats_mislabel() -> None:
    # beds24 schreibt fälschlich "AirBNB", Gast-Domain ist booking.com → Booking.
    body = "AirBNB\nName Gast\nEmail: x@guest.booking.com"
    assert detect_channel(None, body) == "Booking.com"


def test_channel_from_guest_email_param() -> None:
    assert detect_channel("a@guest.airbnb.com") == "Airbnb"


def test_expects_room_flags_multi_room_only() -> None:
    assert expects_room("Münzbach Ferienzimmer") is True
    assert expects_room("Ferienwohnung RebenGlück") is False


# --- Die vier Ticket-Buchungen ---------------------------------------------


def _enrich(subject: str, body: str, property_name: str) -> BookingExtraction:
    base = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING, property_name=property_name
    )
    return enrich_extraction(_email(subject, body), base)


def test_yue_dai_room3_booking() -> None:
    ext = _enrich(
        "Buchung: Münzbach Ferienzimmer : Zimmer Nr. 3 - 88902627 - Booking.com",
        YUE_DAI_BODY,
        "Münzbach Ferienzimmer",
    )
    assert ext.room_number == "3"
    assert ext.channel == "Booking.com"


def test_anetta_room1_booking() -> None:
    ext = _enrich(
        "Buchung: Münzbach Ferienzimmer : Zimmer Nr. 1 - Booking.com",
        _beds24_body("Münzbach Ferienzimmer", "Zimmer Nr. 1\n", "a@guest.booking.com"),
        "Münzbach Ferienzimmer",
    )
    assert ext.room_number == "1"
    assert ext.channel == "Booking.com"


def test_tobias_storno_room1_no_cross_contamination() -> None:
    # Storno-Mail nennt Nr. 1 — selbst wenn der LLM-property_name fälschlich
    # 'Zimmer Nr. 3' enthielte, kommt die Nummer aus DIESEM Mail-Body.
    ext = _enrich(
        "Storno: Münzbach Ferienzimmer : Zimmer Nr. 1 - 86710654 - Booking.com",
        _beds24_body("Münzbach Ferienzimmer", "Zimmer Nr. 1\n", "t@guest.booking.com"),
        "Münzbach Ferienzimmer - Zimmer Nr. 3",
    )
    assert ext.room_number == "1"


def test_rebenglueck_no_room() -> None:
    ext = _enrich(
        "Buchung: Ferienwohnung RebenGlück - Booking.com",
        _beds24_body(
            "Ferienwohnung RebenGlück",
            "Apartment mit 2 Schlafzimmern und Balkon\n",
            "w@guest.booking.com",
        ),
        "Ferienwohnung RebenGlück",
    )
    assert ext.room_number is None
    assert ext.channel == "Booking.com"


# --- Anzeige im Notification-Template (ohne Meta-Änderung) ------------------


def test_property_display_with_room_and_channel() -> None:
    ext = BookingExtraction(
        property_name="Münzbach Ferienzimmer",
        room_number="3",
        channel="Booking.com",
    )
    assert (
        _property_display(ext, "de")
        == "Münzbach Ferienzimmer - Zimmer Nr. 3 (Booking.com)"
    )


def test_property_display_whole_apartment_omits_room() -> None:
    ext = BookingExtraction(
        property_name="Ferienwohnung RebenGlück", channel="Booking.com"
    )
    assert _property_display(ext, "de") == "Ferienwohnung RebenGlück (Booking.com)"

"""Quelldaten-Konsistenzprüfung (Zimmer-/Kanal-Widersprüche)."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.source_consistency import detect_source_conflicts
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail


def _email(subject: str, body: str) -> StoredEmail:
    return StoredEmail(
        message_id="m@test",
        from_address="bookings@beds24.com",
        subject=subject,
        body_text=body,
        received_at=datetime.now(UTC),
        correlation_id="corr",
        processing_state=ProcessingState.CLASSIFIED,
        account_id="acc",
    )


def _codes(conflicts: list) -> set[str]:
    return {c.code for c in conflicts}


def test_room_subject_body_mismatch_escalates() -> None:
    email = _email(
        "Storno: Münzbach Ferienzimmer : Zimmer Nr. 3 - Booking.com",
        "Münzbach Ferienzimmer\nZimmer Nr. 1\nBuchungsnummer: 1\n"
        "Email: g@guest.booking.com\n",
    )
    ext = BookingExtraction(
        intent=BookingIntent.CANCELLATION, property_name="Münzbach Ferienzimmer"
    )
    conflicts = detect_source_conflicts(email, ext)
    assert _codes(conflicts) == {"room_mismatch"}
    assert conflicts[0].escalate is True


def test_missing_room_on_multi_room_escalates() -> None:
    email = _email(
        "Buchung: Münzbach Ferienzimmer - Booking.com",
        "Münzbach Ferienzimmer\nBuchungsnummer: 2\nEmail: g@guest.booking.com\n",
    )
    ext = BookingExtraction(property_name="Münzbach Ferienzimmer")
    conflicts = detect_source_conflicts(email, ext)
    assert "room_missing" in _codes(conflicts)
    assert all(c.escalate for c in conflicts if c.code == "room_missing")


def test_channel_line_vs_domain_mismatch_is_info() -> None:
    email = _email(
        "Buchung: Münzbach Ferienzimmer : Zimmer Nr. 2 - Airbnb",
        "Münzbach Ferienzimmer\nZimmer Nr. 2\nAirbnb HM12345\n"
        "Email: g@guest.booking.com\n",
    )
    ext = BookingExtraction(property_name="Münzbach Ferienzimmer")
    conflicts = detect_source_conflicts(email, ext)
    channel = [c for c in conflicts if c.code == "channel_mismatch"]
    assert channel and channel[0].escalate is False


def test_clean_mail_has_no_conflicts() -> None:
    email = _email(
        "Buchung: Münzbach Ferienzimmer : Zimmer Nr. 3 - Booking.com",
        "Münzbach Ferienzimmer\nZimmer Nr. 3\nBooking.com 5628649148\n"
        "Email: ydai@guest.booking.com\n",
    )
    ext = BookingExtraction(property_name="Münzbach Ferienzimmer")
    assert detect_source_conflicts(email, ext) == []


def test_unit_name_airbnb_does_not_false_flag() -> None:
    # RebenGlück: Unit-Name enthält "Air BNB", Kanal ist aber Booking.com.
    email = _email(
        "Buchung: Ferienwohnung RebenGlück - Booking.com",
        "Rebenglück Air BNB\nApartment mit 2 Schlafzimmern\n"
        "Booking.com 5283424454\nEmail: w@guest.booking.com\n",
    )
    ext = BookingExtraction(property_name="Ferienwohnung RebenGlück")
    assert detect_source_conflicts(email, ext) == []

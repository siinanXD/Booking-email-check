"""Retrieval-Tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

from models.email import StoredEmail
from models.entities import Guest, Reservation
from schemas.booking.extraction import BookingExtraction
from services.retrieval import RetrievalService


def test_find_reservations_by_guest_email(
    entity_repo,
    email_repo,
) -> None:
    guest = Guest(guest_id="g1", email="guest@test.com", name="Max")
    entity_repo.upsert_guest(guest)
    entity_repo.upsert_reservation(
        Reservation(
            reservation_id="r1",
            guest_id="g1",
            booking_number="AB100",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
        )
    )
    email = StoredEmail(
        message_id="m-ret-1",
        from_address="x@y.com",
        body_text="Hi",
        received_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(email)
    svc = RetrievalService(entity_repo, email_repo)
    hits = svc.retrieve(
        email,
        BookingExtraction(email="guest@test.com", booking_number="AB100"),
    )
    assert hits.reservations is not None
    assert len(hits.reservations) >= 1
    assert hits.reservations[0].booking_number == "AB100"

"""Extraktionsschema Booking (Schritt 2+)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from backend.ai.domain.booking.taxonomy import BookingIntent


class BookingExtraction(BaseModel):
    """Strukturierte Felder aus einer Buchungsmail."""

    intent: BookingIntent | None = None
    guest_name: str | None = None
    booking_number: str | None = None
    property_name: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    price: float | None = None
    guest_count: int | None = None
    phone: str | None = None
    email: str | None = None
    platform: str | None = None
    status: str | None = None
    timestamp: datetime | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def parse_stored_extraction(
    stored: BookingExtraction | None,
) -> BookingExtraction | None:
    """Normalisiert gespeicherte Extraktionen für Domain-Queries."""
    return stored

"""Extraktionsschema Booking (Schritt 2+)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from backend.ai.domain.booking.taxonomy import BookingIntent


class BookingExtraction(BaseModel):
    """Strukturierte Felder aus einer Buchungsmail."""

    intent: BookingIntent | None = None
    guest_name: str | None = None
    # Die Frage/Mitteilung des Gastes im Wortlaut — ohne Portal-Rahmentext
    # (Buttons, Antwortfristen, FAQ). Ohne dieses Feld existiert das eigentliche
    # Anliegen nirgends als Datum: der Entwurf griff Stichworte auf, ohne sie als
    # gestellte Frage zu erkennen ("welche Fragen hast du — z. B. Parkplätze?"
    # an einen Gast, der genau danach gefragt hatte).
    guest_message: str | None = None
    booking_number: str | None = None
    property_name: str | None = None
    # Zimmernummer bei Multi-Zimmer-Objekten (z. B. "3" aus "Zimmer Nr. 3").
    # Bleibt separat vom property_name, damit Objekt-Aggregation sauber bleibt.
    room_number: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    price: float | None = None
    guest_count: int | None = None
    phone: str | None = None
    email: str | None = None
    platform: str | None = None
    # Buchungskanal (Booking.com/Airbnb/…), deterministisch aus Mail abgeleitet.
    channel: str | None = None
    status: str | None = None
    timestamp: datetime | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def parse_stored_extraction(
    stored: BookingExtraction | None,
) -> BookingExtraction | None:
    """Normalisiert gespeicherte Extraktionen für Domain-Queries."""
    return stored

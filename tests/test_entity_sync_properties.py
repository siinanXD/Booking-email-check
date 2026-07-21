"""Tests: Objektkatalog aus Buchungsmails — keine Zimmer-Dubletten.

Beim Kunden standen drei Objekte für dieselbe Wohnung im Katalog:
"Münzbach Ferienzimmer", "Münzbach Ferienzimmer - Zimmer Nr. 3" und
"Münzbach Ferienzimmer Zimmer Nr. 3". Ursache war der Exact-Match auf den
Rohnamen aus der Extraktion — jede Schreibweise legte ein eigenes Objekt an.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.ai.domain.booking.beds24_fields import strip_room_designation
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import StoredEmail
from backend.features.booking.entity_sync import ensure_property_from_extraction
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.property_repository import PropertyRepository

ACCOUNT = "acc-1"


def _email() -> StoredEmail:
    return StoredEmail(
        message_id="m-1",
        correlation_id="c-1",
        account_id=ACCOUNT,
        from_address="noreply@booking.com",
        subject="Neue Buchung: Münzbach Ferienzimmer",
        body_text="Buchungsnummer 123",
        received_at=datetime(2026, 7, 1, tzinfo=UTC),
        platform="booking.com",
    )


def _extraction(property_name: str) -> BookingExtraction:
    return BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        guest_name="Max Muster",
        booking_number="BN-1",
        property_name=property_name,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Münzbach Ferienzimmer - Zimmer Nr. 3", "Münzbach Ferienzimmer"),
        ("Münzbach Ferienzimmer Zimmer Nr. 3", "Münzbach Ferienzimmer"),
        ("Münzbach Ferienzimmer : Zimmer Nr.1", "Münzbach Ferienzimmer"),
        ("Münzbach Ferienzimmer, Zimmer Nummer 2", "Münzbach Ferienzimmer"),
        ("Ferienwohnung RebenGlück", "Ferienwohnung RebenGlück"),
        # Ohne Restnamen bleibt der Rohname stehen — leer waere schlechter.
        ("Zimmer Nr. 3", "Zimmer Nr. 3"),
        ("", ""),
    ],
)
def test_strip_room_designation(raw: str, expected: str) -> None:
    """Die Zimmerangabe faellt weg, der Objektname bleibt."""
    assert strip_room_designation(raw) == expected


def test_zimmer_variante_legt_kein_zweites_objekt_an(mock_db: Db) -> None:
    """Der gemeldete Fehler: drei Schreibweisen, ein Objekt."""
    for name in (
        "Münzbach Ferienzimmer",
        "Münzbach Ferienzimmer - Zimmer Nr. 3",
        "Münzbach Ferienzimmer Zimmer Nr. 3",
    ):
        ensure_property_from_extraction(mock_db, ACCOUNT, _email(), _extraction(name))

    names = [p.name for p in PropertyRepository(mock_db).list_all(account_id=ACCOUNT)]
    assert names == ["Münzbach Ferienzimmer"]


def test_zimmer_variante_zuerst_legt_objekt_ohne_zimmer_an(mock_db: Db) -> None:
    """Auch wenn die Zimmer-Schreibweise zuerst kommt, bleibt der Katalog sauber."""
    ensure_property_from_extraction(
        mock_db,
        ACCOUNT,
        _email(),
        _extraction("Münzbach Ferienzimmer - Zimmer Nr. 3"),
    )
    ensure_property_from_extraction(
        mock_db, ACCOUNT, _email(), _extraction("Münzbach Ferienzimmer")
    )

    names = [p.name for p in PropertyRepository(mock_db).list_all(account_id=ACCOUNT)]
    assert names == ["Münzbach Ferienzimmer"]


def test_echtes_zweites_objekt_wird_angelegt(mock_db: Db) -> None:
    """Die Entdoppelung darf keine eigenstaendige Unterkunft schlucken."""
    ensure_property_from_extraction(
        mock_db, ACCOUNT, _email(), _extraction("Münzbach Ferienzimmer")
    )
    ensure_property_from_extraction(
        mock_db, ACCOUNT, _email(), _extraction("Ferienwohnung RebenGlück")
    )

    names = sorted(
        p.name for p in PropertyRepository(mock_db).list_all(account_id=ACCOUNT)
    )
    assert names == ["Ferienwohnung RebenGlück", "Münzbach Ferienzimmer"]

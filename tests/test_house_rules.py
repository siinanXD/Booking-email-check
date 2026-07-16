"""Hausregeln als Wissensquelle für Antwortentwürfe.

Ohne sie kann ein Entwurf inhaltliche Gastfragen ("Gibt es Parkplätze?") nicht
beantworten — er hat schlicht keine Quelle. `notes` ist bewusst nicht diese
Quelle: die sind intern und dürfen nie an Gäste.
"""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services.grounding import GroundingService
from backend.ai.services.retrieval import RetrievalHits, RetrievalService
from backend.core.models.email import StoredEmail
from backend.core.models.entities import Property, Reservation
from backend.core.models.response import GeneratedResponse
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.entity_repository import EntityRepository
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.property_repository import PropertyRepository

ACCOUNT = "acc-1"
PROPERTY = "Münzbach Ferienzimmer"
RULES = "Parken: kostenlos direkt vor dem Haus.\nCheck-in ab 16:00."


def _email() -> StoredEmail:
    return StoredEmail(
        message_id="m1",
        from_address="gast@example.com",
        subject="Anfrage",
        body_text="Gibt es Parkplätze?",
        received_at=date(2026, 7, 17),  # type: ignore[arg-type]
        correlation_id="c1",
        account_id=ACCOUNT,
    )


def _retrieval(mock_db: Db) -> RetrievalService:
    return RetrievalService(
        EntityRepository(mock_db),
        EmailRepository(mock_db),
        property_repo=PropertyRepository(mock_db),
    )


def _seed_property(mock_db: Db, *, rules: str | None) -> None:
    PropertyRepository(mock_db).upsert(
        Property(
            property_id="p1",
            name=PROPERTY,
            account_id=ACCOUNT,
            notes="INTERN: Schlüsseltresor-Code 4711",
            house_rules=rules,
        ),
        account_id=ACCOUNT,
    )


def test_hausregeln_landen_im_kontext(mock_db: Db) -> None:
    _seed_property(mock_db, rules=RULES)

    hits = _retrieval(mock_db).retrieve(
        _email(), BookingExtraction(property_name=PROPERTY)
    )

    assert hits.house_rules == RULES


def test_ohne_hausregeln_bleibt_der_kontext_leer(mock_db: Db) -> None:
    """Kein Eintrag → keine Quelle. Der Entwurf soll dann nicht raten."""
    _seed_property(mock_db, rules=None)

    hits = _retrieval(mock_db).retrieve(
        _email(), BookingExtraction(property_name=PROPERTY)
    )

    assert hits.house_rules is None


def test_fremde_unterkunft_liefert_keine_regeln(mock_db: Db) -> None:
    """Lieber keine Regeln als die einer anderen Wohnung."""
    _seed_property(mock_db, rules=RULES)

    hits = _retrieval(mock_db).retrieve(
        _email(), BookingExtraction(property_name="Ferienwohnung RebenGlück")
    )

    assert hits.house_rules is None


def test_fremder_mandant_sieht_keine_regeln(mock_db: Db) -> None:
    _seed_property(mock_db, rules=RULES)
    email = _email()
    email.account_id = "acc-2"

    hits = _retrieval(mock_db).retrieve(
        email, BookingExtraction(property_name=PROPERTY)
    )

    assert hits.house_rules is None


def test_datum_aus_hausregeln_ist_kein_grounding_fehler() -> None:
    """Regressionsschutz: Hausregeln sind eine erlaubte Faktenquelle.

    Ohne sie in `_allowed_dates` schlüge der Check bei einem korrekt zitierten
    Datum aus den Hausregeln fehl — ein Fehlalarm, der den Entwurf eskaliert.
    """
    hits = RetrievalHits(
        reservations=[
            Reservation(
                reservation_id="r1",
                booking_number="88902627",
                check_in=date(2026, 9, 9),
                check_out=date(2026, 9, 12),
            )
        ],
        house_rules="Die Sauna ist vom 01.01.2027 bis 06.01.2027 geschlossen.",
    )
    draft = GeneratedResponse(
        correlation_id="c1",
        body="Die Sauna ist vom 01.01.2027 bis 06.01.2027 geschlossen.",
        model="test",
    )

    result = GroundingService().check_with_detail(draft, hits)

    assert result.ok, result.failed_fields


def test_erfundenes_datum_faellt_weiterhin_auf() -> None:
    """Die Lockerung darf den Check nicht generell aushebeln."""
    hits = RetrievalHits(
        reservations=[
            Reservation(
                reservation_id="r1",
                booking_number="88902627",
                check_in=date(2026, 9, 9),
                check_out=date(2026, 9, 12),
            )
        ],
        house_rules=RULES,
    )
    draft = GeneratedResponse(
        correlation_id="c1",
        body="Ihr Aufenthalt beginnt am 24.12.2026.",
        model="test",
    )

    result = GroundingService().check_with_detail(draft, hits)

    assert not result.ok
    assert "date" in result.failed_fields

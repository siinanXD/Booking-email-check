"""Synchronisiert Unterkunftsnamen aus Extraktionen in die Properties-Collection."""

from __future__ import annotations

import hashlib

from backend.ai.domain.booking.beds24_fields import strip_room_designation
from backend.ai.domain.booking.booking_relevance import classify_booking_mail
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.property_match import match_known_property_name
from backend.core.models.email import StoredEmail
from backend.core.models.entities import Property
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.property_repository import PropertyRepository


def _property_id(account_id: str, name: str) -> str:
    digest = hashlib.sha256(f"{account_id}:{name.lower()}".encode()).hexdigest()[:24]
    return f"prop_{digest}"


def ensure_property_from_extraction(
    db: Db,
    account_id: str,
    email: StoredEmail,
    extraction: BookingExtraction | None,
) -> None:
    """Legt eine Unterkunft an, wenn die Extraktion einen neuen Namen liefert."""
    if extraction is None:
        return
    if not classify_booking_mail(email, extraction).is_booking:
        return
    # Die Zimmerangabe gehört nach `room_number`, nicht in den Objektnamen —
    # sonst wird aus jeder Schreibweise desselben Listings ein eigenes Objekt.
    name = strip_room_designation(extraction.property_name)
    if not name:
        return
    prop_repo = PropertyRepository(db)
    # Auch archivierte Objekte zählen: ein bewusst gelöschtes Objekt darf
    # nicht durch die nächste Buchungsmail wieder auferstehen.
    existing = [
        p.name.strip()
        for p in prop_repo.list_all(account_id=account_id, include_inactive=True)
        if p.name and p.name.strip()
    ]
    # Wortgenauer Abgleich statt Exact-Match: eine Namensvariante, die ein
    # bekanntes Objekt als ganze Wortfolge enthält, ist dasselbe Objekt.
    if match_known_property_name(name, existing):
        return
    prop_repo.upsert(
        Property(
            property_id=_property_id(account_id, name),
            name=name,
            platform=extraction.platform or email.platform,
            account_id=account_id,
        ),
        account_id=account_id,
    )

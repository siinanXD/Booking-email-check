"""Synchronisiert Unterkunftsnamen aus Extraktionen in die Properties-Collection."""

from __future__ import annotations

import hashlib

from backend.ai.domain.booking.booking_relevance import classify_booking_mail
from backend.ai.domain.booking.extraction import parse_stored_extraction
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail
from backend.core.models.entities import Property
from backend.infrastructure.repositories.property_repository import PropertyRepository


def sync_properties_from_extractions(
    ctx: AppContext,
    account_id: str,
    *,
    limit: int = 500,
) -> int:
    """Legt fehlende Property-Dokumente aus Extraktionen an."""
    prop_repo = PropertyRepository(ctx.db)
    props = prop_repo.list_all(account_id=account_id)
    existing = {p.name.strip().lower() for p in props}
    created = 0
    match: dict[str, object] = {"account_id": account_id}
    for doc in ctx.email_repo._col.find(match).sort("received_at", -1).limit(limit):
        email = StoredEmail.from_mongo(doc)
        ext = parse_stored_extraction(
            ctx.extraction_repo.get_by_correlation_id(
                email.correlation_id,
                account_id=account_id,
            )
        )
        if not classify_booking_mail(email, ext).is_booking:
            continue
        name = (ext.property_name if ext else None) or ""
        key = name.strip()
        if not key or key.lower() in existing:
            continue
        prop_id = _property_id(account_id, key)
        prop_repo.upsert(
            Property(
                property_id=prop_id,
                name=key,
                platform=ext.platform if ext else email.platform,
                account_id=account_id,
            ),
            account_id=account_id,
        )
        existing.add(key.lower())
        created += 1
    return created


def _property_id(account_id: str, name: str) -> str:
    digest = hashlib.sha256(f"{account_id}:{name.lower()}".encode()).hexdigest()[:24]
    return f"prop_{digest}"


def ensure_property_from_extraction(
    db: object,
    account_id: str,
    email: StoredEmail,
    extraction: object | None,
) -> None:
    """Legt eine Unterkunft an, wenn die Extraktion einen neuen Namen liefert."""
    from backend.ai.domain.booking.extraction import BookingExtraction

    if not isinstance(extraction, BookingExtraction):
        return
    if not classify_booking_mail(email, extraction).is_booking:
        return
    name = (extraction.property_name or "").strip()
    if not name:
        return
    prop_repo = PropertyRepository(db)
    existing = {
        p.name.strip().lower() for p in prop_repo.list_all(account_id=account_id)
    }
    if name.lower() in existing:
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

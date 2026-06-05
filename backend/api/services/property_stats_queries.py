"""Unterkunfts-Historie und Jahres-KPIs aus Mails."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.booking_relevance import classify_booking_mail
from backend.api.schemas.properties import (
    PropertyHistoryItem,
    PropertyHistoryResponse,
    PropertyYearStats,
)
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail
from backend.infrastructure.repositories.property_repository import PropertyRepository


def property_history(
    ctx: AppContext,
    account_id: str,
    *,
    property_name: str | None = None,
    limit: int = 50,
) -> PropertyHistoryResponse:
    items: list[PropertyHistoryItem] = []
    match: dict[str, object] = {"account_id": account_id}
    cursor = (
        ctx.email_repo._col.find(match)
        .sort("received_at", -1)
        .limit(min(max(limit * 3, 1), 500))
    )
    needle = (property_name or "").strip().lower()
    for doc in cursor:
        email = StoredEmail.from_mongo(doc)
        ext = ctx.extraction_repo.get_by_correlation_id(
            email.correlation_id,
            account_id=account_id,
        )
        if not classify_booking_mail(email, ext).is_booking:
            continue
        prop = (ext.property_name if ext else None) or ""
        if needle and prop.strip().lower() != needle:
            continue
        items.append(
            PropertyHistoryItem(
                correlation_id=email.correlation_id,
                subject=email.subject,
                received_at=(
                    email.received_at.isoformat() if email.received_at else None
                ),
                intent=ext.intent.value if ext and ext.intent else None,
                booking_number=ext.booking_number if ext else None,
                property_name=prop or None,
            )
        )
        if len(items) >= limit:
            break
    return PropertyHistoryResponse(items=items, total=len(items))


def _booking_matches_year(
    email: StoredEmail,
    *,
    year: int,
    check_in: date | None,
) -> bool:
    if check_in is not None:
        return check_in.year == year
    received = email.received_at
    return received is not None and received.year == year


def aggregate_property_year_stats(
    ctx: AppContext,
    account_id: str,
    property_name: str,
    *,
    year: int,
) -> PropertyYearStats:
    """Aggregiert Buchungs-KPIs für eine Unterkunft in einem Jahr."""
    needle = property_name.strip().lower()
    booked_days = 0
    revenue = 0.0
    booking_count = 0
    incomplete_data_count = 0
    match: dict[str, object] = {"account_id": account_id}
    for doc in ctx.email_repo._col.find(match).sort("received_at", -1).limit(2000):
        email = StoredEmail.from_mongo(doc)
        ext = ctx.extraction_repo.get_by_correlation_id(
            email.correlation_id,
            account_id=account_id,
        )
        if not classify_booking_mail(email, ext).is_booking or ext is None:
            continue
        prop = (ext.property_name or "").strip()
        if prop.lower() != needle:
            continue
        if not _booking_matches_year(email, year=year, check_in=ext.check_in):
            continue
        booking_count += 1
        has_dates = ext.check_in is not None and ext.check_out is not None
        has_price = ext.price is not None
        if not has_dates or not has_price:
            incomplete_data_count += 1
        if ext.check_in and ext.check_out:
            days = (ext.check_out - ext.check_in).days
            if days > 0:
                booked_days += days
        if ext.price is not None:
            revenue += float(ext.price)
    return PropertyYearStats(
        year=year,
        booked_days=booked_days,
        revenue=revenue,
        booking_count=booking_count,
        incomplete_data_count=incomplete_data_count,
    )


def property_year_stats(
    ctx: AppContext,
    account_id: str,
    property_id: str,
    *,
    year: int,
) -> PropertyYearStats | None:
    """Jahres-KPIs für eine Unterkunft anhand der Property-ID."""
    prop = PropertyRepository(ctx.db).get_by_id(property_id, account_id=account_id)
    if prop is None:
        return None
    return aggregate_property_year_stats(
        ctx,
        account_id,
        prop.name,
        year=year,
    )

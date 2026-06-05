"""KI-Vorschläge für neue Unterkunftsnamen."""

from __future__ import annotations

from backend.ai.domain.booking.booking_relevance import classify_booking_mail
from backend.ai.domain.booking.extraction import parse_stored_extraction
from backend.api.schemas.properties import (
    PropertySuggestion,
    PropertySuggestionsResponse,
)
from backend.api.services.tenant_properties import list_property_names
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail


def property_suggestions(
    ctx: AppContext,
    account_id: str,
    *,
    limit: int = 20,
) -> PropertySuggestionsResponse:
    known = {n.lower() for n in list_property_names(ctx, account_id)}
    counts: dict[str, int] = {}
    match: dict[str, object] = {"account_id": account_id}
    for doc in ctx.email_repo._col.find(match).sort("received_at", -1).limit(800):
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
        if not key or key.lower() in known:
            continue
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))
    items = [
        PropertySuggestion(property_name=name, mail_count=count)
        for name, count in ranked[:limit]
    ]
    return PropertySuggestionsResponse(items=items)

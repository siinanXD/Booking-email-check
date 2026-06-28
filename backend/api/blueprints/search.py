"""Globale Suche über Buchungen, Unterkünfte und Mails (Topbar-Overlay)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.search import SearchHit, SearchResponse
from backend.api.services.property_crud_queries import list_properties

search_bp = Blueprint("search", __name__, url_prefix="/api/search")

_GROUP_LIMIT = 5


def _mail_hit(email: Any) -> SearchHit:
    received = email.received_at.strftime("%d.%m. %H:%M") if email.received_at else ""
    platform = getattr(email, "platform", None) or "Posteingang"
    subtitle = " · ".join(part for part in (received, platform) if part)
    title = (email.subject or email.from_address or "Mail").strip()
    return SearchHit(
        id=email.correlation_id,
        title=title,
        subtitle=subtitle,
        href="/inbox",
    )


def _booking_hit(email: Any) -> SearchHit:
    received = email.received_at.strftime("%d.%m.%Y") if email.received_at else ""
    sender = (email.from_address or "").split("<")[0].strip()
    subtitle = " · ".join(part for part in (sender, received) if part)
    return SearchHit(
        id=email.correlation_id,
        title=(email.subject or sender or "Buchung").strip(),
        subtitle=subtitle,
        href="/inbox?intent=new_booking",
    )


@search_bp.get("")
@require_auth
@require_account
def search() -> tuple[Any, int]:
    """Liefert gruppierte Treffer für die Topbar-Suche."""
    query = (request.args.get("q") or "").strip()
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    if len(query) < 2:
        return jsonify(SearchResponse().model_dump()), 200

    ctx = g.ctx

    bookings, _ = ctx.email_repo.list_filtered(
        account_id=account_id,
        search=query,
        booking_related=True,
        limit=_GROUP_LIMIT,
    )
    mails, _ = ctx.email_repo.list_filtered(
        account_id=account_id,
        search=query,
        limit=_GROUP_LIMIT,
    )

    needle = query.lower()
    property_hits: list[SearchHit] = []
    try:
        props = list_properties(ctx, account_id)
        for item in props.items:
            if needle in item.name.lower():
                property_hits.append(
                    SearchHit(
                        id=item.property_id,
                        title=item.name,
                        subtitle="Unterkunft",
                        href=f"/properties/{item.property_id}",
                    )
                )
            if len(property_hits) >= _GROUP_LIMIT:
                break
    except Exception:  # noqa: BLE001 - Suche darf nie an einer Gruppe scheitern
        property_hits = []

    response = SearchResponse(
        bookings=[_booking_hit(e) for e in bookings],
        properties=property_hits,
        mails=[_mail_hit(e) for e in mails],
    )
    return jsonify(response.model_dump()), 200

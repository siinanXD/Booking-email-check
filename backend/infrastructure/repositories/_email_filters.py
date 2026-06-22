"""Query-Builder-Hilfsfunktionen für die emails-Collection."""

from __future__ import annotations

from typing import Any


def build_base_match(
    *,
    account_id: str | None,
    status: str | None,
    platform: str | None,
    search: str | None,
    booking_related: bool,
    received_since: str | None,
    received_until: str | None,
) -> dict[str, Any]:
    """Baut den Basis-Filterausdruck für die emails-Collection."""
    match: dict[str, Any] = {}
    if account_id:
        match["account_id"] = account_id
    if received_since or received_until:
        received_filter: dict[str, Any] = {}
        if received_since:
            received_filter["$gte"] = received_since
        if received_until:
            received_filter["$lte"] = received_until
        match["received_at"] = received_filter
    if booking_related:
        # Vorberechnetes Flag statt teurer Regex-/Python-Klassifikation.
        match["is_booking"] = True
    if status:
        match["processing_state"] = status
    if platform:
        match["platform"] = platform
    if search:
        match["$or"] = [
            {"subject": {"$regex": search, "$options": "i"}},
            {"from_address": {"$regex": search, "$options": "i"}},
            {"correlation_id": search},
        ]
    return match


def apply_booking_related_match(
    match_stage: dict[str, Any],
    intent_filter: list[str],
) -> dict[str, Any]:
    """Verschärft Filter: Storno/Gästeanfrage nur mit Buchungsbezug."""
    intent_set = set(intent_filter)
    extra: list[dict[str, Any]] = []
    has_bn = {
        "ext.extraction.booking_number": {
            "$exists": True,
            "$nin": [None, ""],
        }
    }
    booking_subject = {
        "subject": {
            "$regex": (
                r"buchung|booking|reservierung|storno|beds24|airbnb|"
                r"gäste|guest|anreise|übernacht"
            ),
            "$options": "i",
        }
    }
    if "cancellation" in intent_set and intent_set <= {"cancellation"}:
        extra.append(
            {
                "$and": [
                    has_bn,
                    booking_subject,
                ]
            }
        )
    elif "guest_inquiry" in intent_set and intent_set <= {"guest_inquiry"}:
        extra.append({"$or": [has_bn, booking_subject]})
    elif intent_set <= {"change"}:
        extra.append({"$or": [has_bn, booking_subject]})
    if not extra:
        return match_stage
    return {"$and": [match_stage, *extra]}


def build_intent_pipeline(
    base_match: dict[str, Any],
    intent_filter: list[str],
    skip: int,
    limit: int,
    *,
    booking_related: bool,
) -> list[dict[str, Any]]:
    """Baut die Aggregations-Pipeline für Intent-gefilterte Abfragen."""
    intent_match_val: Any = (
        intent_filter[0] if len(intent_filter) == 1 else {"$in": intent_filter}
    )
    match_stage: dict[str, Any] = {
        **base_match,
        "ext.extraction.intent": intent_match_val,
    }
    if booking_related:
        match_stage = apply_booking_related_match(match_stage, intent_filter)
    return [
        {
            "$lookup": {
                "from": "extractions",
                "localField": "correlation_id",
                "foreignField": "_id",
                "as": "ext",
            }
        },
        {"$unwind": {"path": "$ext", "preserveNullAndEmptyArrays": False}},
        {"$match": match_stage},
        {"$sort": {"updated_at": -1}},
        {
            "$facet": {
                "items": [{"$skip": skip}, {"$limit": limit}],
                "total": [{"$count": "count"}],
            }
        },
    ]

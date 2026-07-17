"""Query-Builder-Hilfsfunktionen für die emails-Collection."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection


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


def run_filtered_query(
    col: Collection[dict[str, Any]],
    base_match: dict[str, Any],
    *,
    intent_filter: list[str],
    booking_related: bool,
    skip: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Führt die Listen-Query aus und gibt (Dokumente, Gesamtzahl) zurück.

    Drei Pfade, absichtlich getrennt:
    - booking_related: rein über vorberechnete Felder (kein $lookup, kein
      Python-Loop). Muss deckungsgleich zu ``count_booking_intents`` bleiben.
    - intent ohne booking_related: Aggregations-Pipeline mit $facet.
    - sonst: einfacher find, sortiert nach updated_at.
    """
    if booking_related:
        if intent_filter:
            base_match["effective_intent"] = (
                intent_filter[0] if len(intent_filter) == 1 else {"$in": intent_filter}
            )
        total = int(col.count_documents(base_match))
        cursor = col.find(base_match).sort("received_at", -1).skip(skip).limit(limit)
        return list(cursor), total

    if intent_filter:
        pipeline = build_intent_pipeline(
            base_match, intent_filter, skip, limit, booking_related=booking_related
        )
        agg = list(col.aggregate(pipeline))
        if not agg:
            return [], 0
        total_arr = agg[0].get("total", [])
        total = int(total_arr[0]["count"]) if total_arr else 0
        return list(agg[0].get("items", [])), total

    total = int(col.count_documents(base_match))
    cursor = col.find(base_match).sort("updated_at", -1).skip(skip).limit(limit)
    return list(cursor), total

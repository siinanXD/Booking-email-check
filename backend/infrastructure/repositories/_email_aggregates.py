"""Aggregationen über die `emails`-Collection für das Admin-Datenfluss-Board."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection

from backend.core.models.email import StoredEmail
from backend.infrastructure.repositories.tenant_scope import with_account_filter


def count_states(
    col: Collection[dict[str, Any]],
    since_iso: str,
    account_id: str | None,
) -> dict[str, int]:
    """Anzahl Mails je `processing_state` seit `since_iso` ($group)."""
    match = with_account_filter({"updated_at": {"$gte": since_iso}}, account_id)
    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {"$group": {"_id": "$processing_state", "count": {"$sum": 1}}},
    ]
    return {str(row["_id"]): int(row["count"]) for row in col.aggregate(pipeline)}


def list_stuck(
    col: Collection[dict[str, Any]],
    states: list[str],
    older_than_iso: str,
    account_id: str | None,
    limit: int,
) -> list[StoredEmail]:
    """Mails in `states`, deren `updated_at` älter als `older_than_iso` ist."""
    match = with_account_filter(
        {
            "processing_state": {"$in": list(states)},
            "updated_at": {"$lt": older_than_iso},
        },
        account_id,
    )
    cursor = col.find(match).sort("updated_at", 1).limit(limit)
    return [StoredEmail.from_mongo(doc) for doc in cursor]


def count_booking_intents(
    col: Collection[dict[str, Any]],
    *,
    account_id: str | None,
    received_since: str | None,
    received_until: str | None,
) -> dict[str, int]:
    """Buchungsmails je ``effective_intent`` — die Quelle der Navigations-Zähler.

    Nutzt bewusst dasselbe ``build_base_match`` wie ``EmailRepository.list_filtered``:
    Zähler und Liste müssen strukturell dieselbe Frage stellen, nicht nur zufällig
    dieselbe Antwort geben. Vorher klassifizierten die Zähler bei jedem Request
    live in Python, während die Liste die vorberechneten Felder las — eine Mail
    ohne ``is_booking`` wurde gezählt, war aber über die Liste unauffindbar.
    """
    from backend.infrastructure.repositories._email_filters import build_base_match

    match = build_base_match(
        account_id=account_id,
        status=None,
        platform=None,
        search=None,
        booking_related=True,
        received_since=received_since,
        received_until=received_until,
    )
    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {"$group": {"_id": "$effective_intent", "count": {"$sum": 1}}},
    ]
    return {
        str(row["_id"]): int(row["count"])
        for row in col.aggregate(pipeline)
        if row.get("_id")
    }

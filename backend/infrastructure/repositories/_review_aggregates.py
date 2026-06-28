"""Entscheidungs-Aggregation über die `reviews`-Collection (Admin-Datenfluss).

Bewusst mit `count_documents`/`find` statt `$bucket`/`$facet` — robust unter
mongomock und für ein Admin-Aggregat schnell genug.
"""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection

from backend.infrastructure.repositories.tenant_scope import with_account_filter

# Konfidenz-Buckets (lo inklusiv, hi exklusiv).
_BUCKETS: list[tuple[str, float, float]] = [
    ("0–50%", 0.0, 0.5),
    ("50–70%", 0.5, 0.7),
    ("70–90%", 0.7, 0.9),
    ("90–100%", 0.9, 1.01),
]


def _flag_category(message: str) -> str:
    """Normalisiert eine source_flags-Meldung auf eine Anzeige-Kategorie."""
    low = message.lower()
    if low.startswith("zimmer widersprüchlich"):
        return "Zimmer widersprüchlich"
    if low.startswith("zimmernummer fehlt"):
        return "Zimmer fehlt"
    if low.startswith("kanal widersprüchlich"):
        return "Kanal widersprüchlich"
    return message[:40]


def decision_breakdown(
    col: Collection[dict[str, Any]],
    since_iso: str,
    account_id: str | None,
) -> dict[str, Any]:
    """Entscheidungs-Kennzahlen (auto/human/eskaliert/abgelehnt/offen, Konfidenz)."""

    def count(extra: dict[str, Any]) -> int:
        query = with_account_filter(
            {**extra, "updated_at": {"$gte": since_iso}}, account_id
        )
        return int(col.count_documents(query))

    total = count({})
    grounding_fail = count({"grounding_flag": True})
    buckets = [
        {"bucket": name, "count": count({"confidence": {"$gte": lo, "$lt": hi}})}
        for name, lo, hi in _BUCKETS
    ]

    flags: dict[str, int] = {}
    flag_query = with_account_filter(
        {"updated_at": {"$gte": since_iso}, "source_flags": {"$ne": []}},
        account_id,
    )
    for doc in col.find(flag_query, {"source_flags": 1}):
        for message in doc.get("source_flags") or []:
            category = _flag_category(str(message))
            flags[category] = flags.get(category, 0) + 1
    top = sorted(flags.items(), key=lambda kv: (-kv[1], kv[0]))[:10]

    return {
        "auto_approved": count({"review_status": "approved", "auto_approved": True}),
        "human_approved": count(
            {"review_status": "approved", "auto_approved": {"$ne": True}}
        ),
        "rejected": count({"review_status": "rejected"}),
        "pending": count({"review_status": "pending"}),
        "escalated": count({"escalated": True}),
        "grounding": {"ok": max(0, total - grounding_fail), "fail": grounding_fail},
        "confidence_buckets": buckets,
        "top_source_flags": [{"flag": name, "count": n} for name, n in top],
    }

"""Absender-bezogene Query-Helfer für DSGVO-Funktionen (Auskunft/Löschung)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from backend.core.models.email import StoredEmail
from backend.infrastructure.repositories.tenant_scope import with_account_filter

if TYPE_CHECKING:
    from pymongo.collection import Collection


def sender_match_query(
    from_address: str,
    account_id: str | None,
) -> dict[str, Any] | None:
    """Account-scoped, case-insensitive Match auf eine exakte Absender-Adresse.

    Gibt ``None`` zurück, wenn die Adresse leer ist (kein Treffer).
    """
    needle = from_address.strip()
    if not needle:
        return None
    pattern = f"^{re.escape(needle)}$"
    return with_account_filter(
        {"from_address": {"$regex": pattern, "$options": "i"}},
        account_id,
    )


def list_emails_by_sender(
    col: Collection[dict[str, Any]],
    from_address: str,
    account_id: str | None,
) -> list[StoredEmail]:
    """Alle Mails eines Absenders (case-insensitive), für DSGVO-Auskunft."""
    query = sender_match_query(from_address, account_id)
    if query is None:
        return []
    cursor = col.find(query).sort("received_at", -1)
    return [StoredEmail.from_mongo(doc) for doc in cursor]


def delete_emails_by_sender(
    col: Collection[dict[str, Any]],
    from_address: str,
    account_id: str | None,
) -> tuple[int, list[str]]:
    """Löscht alle Mails eines Absenders. Gibt (Anzahl, Correlation-IDs) zurück."""
    query = sender_match_query(from_address, account_id)
    if query is None:
        return 0, []
    correlation_ids = [
        e.correlation_id for e in list_emails_by_sender(col, from_address, account_id)
    ]
    result = col.delete_many(query)
    return int(result.deleted_count), correlation_ids

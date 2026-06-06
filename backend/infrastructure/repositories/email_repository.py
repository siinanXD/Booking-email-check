"""Persistenz eingegangener E-Mails."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories._email_filters import (
    build_base_match,
    build_intent_pipeline,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class EmailRepository:
    """CRUD für die Collection `emails`."""

    COLLECTION = "emails"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index(
            [("account_id", 1), ("received_at", -1)],
            name="idx_email_account_received",
        )
        self._col.create_index(
            [("account_id", 1), ("updated_at", -1)],
            name="idx_email_account_updated",
        )
        self._col.create_index(
            [("account_id", 1), ("correlation_id", 1)],
            name="idx_email_account_correlation",
        )
        self._col.create_index(
            [("account_id", 1), ("message_id", 1)],
            name="idx_email_account_message",
        )

    def find_existing_message_ids(
        self,
        message_ids: list[str],
        *,
        account_id: str | None = None,
    ) -> set[str]:
        """Welche Message-IDs bereits gespeichert sind (Batch-Dedup für Poll)."""
        if not message_ids:
            return set()
        query = with_account_filter({"_id": {"$in": message_ids}}, account_id)
        found = {str(doc["_id"]) for doc in self._col.find(query, {"_id": 1})}
        missing = [mid for mid in message_ids if mid not in found]
        if not missing:
            return found
        alt_query = with_account_filter({"message_id": {"$in": missing}}, account_id)
        for doc in self._col.find(alt_query, {"_id": 1, "message_id": 1}):
            found.add(str(doc.get("message_id") or doc["_id"]))
        return found

    def upsert_by_message_id(self, email: StoredEmail) -> StoredEmail:
        """Idempotentes Speichern nach Message-ID."""
        now = datetime.now(UTC)
        doc = email.to_mongo()
        doc["updated_at"] = now.isoformat()
        if email.created_at is None:
            doc["created_at"] = now.isoformat()
        self._col.update_one(
            {"_id": email.message_id},
            {"$set": doc},
            upsert=True,
        )
        stored = self.get_by_message_id(email.message_id)
        if stored is None:
            msg = f"Upsert failed for message_id={email.message_id}"
            raise RuntimeError(msg)
        return stored

    def get_by_message_id(
        self,
        message_id: str,
        *,
        account_id: str | None = None,
    ) -> StoredEmail | None:
        """Lädt eine Mail anhand der Message-ID."""
        query = with_account_filter({"_id": message_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None:
            alt = with_account_filter({"message_id": message_id}, account_id)
            doc = self._col.find_one(alt)
        if doc is None:
            return None
        return StoredEmail.from_mongo(doc)

    def update_processing_state(
        self,
        message_id: str,
        state: ProcessingState,
        *,
        account_id: str | None = None,
        **extra: Any,
    ) -> StoredEmail | None:
        """Aktualisiert Verarbeitungsstatus und optionale Felder."""
        update: dict[str, Any] = {
            "processing_state": state.value,
            "updated_at": datetime.now(UTC).isoformat(),
            **extra,
        }
        query = with_account_filter({"_id": message_id}, account_id)
        self._col.update_one(query, {"$set": update})
        return self.get_by_message_id(message_id, account_id=account_id)

    def list_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> list[StoredEmail]:
        """Alle Mails einer Correlation-ID."""
        query = with_account_filter({"correlation_id": correlation_id}, account_id)
        cursor = self._col.find(query)
        return [StoredEmail.from_mongo(doc) for doc in cursor]

    def get_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> StoredEmail | None:
        """Erste Mail zu einer Correlation-ID."""
        query = with_account_filter({"correlation_id": correlation_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None:
            return None
        return StoredEmail.from_mongo(doc)

    def list_by_correlation_ids(
        self,
        correlation_ids: list[str],
        *,
        account_id: str | None = None,
    ) -> list[StoredEmail]:
        """Mails zu einer Liste von Correlation-IDs (Reihenfolge unbestimmt)."""
        if not correlation_ids:
            return []
        query = with_account_filter(
            {"correlation_id": {"$in": correlation_ids}},
            account_id,
        )
        cursor = self._col.find(query)
        return [StoredEmail.from_mongo(doc) for doc in cursor]

    def list_filtered(
        self,
        *,
        account_id: str | None = None,
        status: str | None = None,
        intent: str | None = None,
        intents: list[str] | None = None,
        platform: str | None = None,
        search: str | None = None,
        booking_related: bool = False,
        page: int = 1,
        limit: int = 20,
        received_since: str | None = None,
        received_until: str | None = None,
    ) -> tuple[list[StoredEmail], int]:
        """Paginierte Liste mit optionalen Filtern."""
        base_match = build_base_match(
            account_id=account_id,
            status=status,
            platform=platform,
            search=search,
            booking_related=booking_related,
            received_since=received_since,
            received_until=received_until,
        )
        skip = max(page - 1, 0) * limit
        intent_filter: list[str] = intents or ([intent] if intent else [])

        if intent_filter:
            pipeline = build_intent_pipeline(
                base_match, intent_filter, skip, limit, booking_related=booking_related
            )
            agg = list(self._col.aggregate(pipeline))
            if not agg:
                return [], 0
            items_raw = agg[0].get("items", [])
            total_arr = agg[0].get("total", [])
            total = int(total_arr[0]["count"]) if total_arr else 0
            return [StoredEmail.from_mongo(doc) for doc in items_raw], total

        total = int(self._col.count_documents(base_match))
        cursor = (
            self._col.find(base_match).sort("updated_at", -1).skip(skip).limit(limit)
        )
        return [StoredEmail.from_mongo(doc) for doc in cursor], total

    def count_by_state_since(
        self,
        state: ProcessingState,
        since_iso: str,
        *,
        account_id: str | None = None,
    ) -> int:
        """Zählt Mails mit Status seit Zeitstempel (ISO)."""
        query = with_account_filter(
            {
                "processing_state": state.value,
                "updated_at": {"$gte": since_iso},
            },
            account_id,
        )
        return int(self._col.count_documents(query))

    def count_updated_since(
        self,
        since_iso: str,
        *,
        account_id: str | None = None,
    ) -> int:
        """Alle Mails mit Update seit Zeitstempel."""
        query = with_account_filter({"updated_at": {"$gte": since_iso}}, account_id)
        return int(self._col.count_documents(query))

    def count_received_since(
        self,
        since_iso: str,
        *,
        account_id: str | None = None,
    ) -> int:
        """Eingegangene Mails seit Zeitstempel (received_at, ISO)."""
        query = with_account_filter({"received_at": {"$gte": since_iso}}, account_id)
        return int(self._col.count_documents(query))

    def max_received_at(self, *, account_id: str | None = None) -> str | None:
        """Neuestes received_at in der Inbox (ISO-String)."""
        query = with_account_filter({}, account_id)
        doc = self._col.find_one(query, sort=[("received_at", -1)])
        if doc is None:
            return None
        received_at = doc.get("received_at")
        if received_at is None:
            return None
        return str(received_at)

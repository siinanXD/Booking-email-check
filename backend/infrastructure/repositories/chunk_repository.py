"""Text-Chunks pro Mail (mandantenscharf, getrennt von Vektoren)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from backend.infrastructure.repositories.domain_collections import CHUNKS
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class ChunkRepository:
    """Collection `chunks` — Rohtext-Segmente für Indexierung."""

    COLLECTION = CHUNKS

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("correlation_id", 1)])

    def upsert_chunk(
        self,
        chunk_id: str,
        correlation_id: str,
        text: str,
        intent: str | None = None,
        *,
        account_id: str | None = None,
        chunk_index: int | None = None,
        token_count: int | None = None,
        char_start: int | None = None,
        char_end: int | None = None,
        context_prefix: str | None = None,
    ) -> None:
        """Speichert einen Text-Chunk."""
        doc: dict[str, Any] = {
            "_id": chunk_id,
            "correlation_id": correlation_id,
            "text": text,
            "intent": intent,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if account_id:
            doc["account_id"] = account_id
        if chunk_index is not None:
            doc["chunk_index"] = chunk_index
        if token_count is not None:
            doc["token_count"] = token_count
        if char_start is not None:
            doc["char_start"] = char_start
        if char_end is not None:
            doc["char_end"] = char_end
        if context_prefix is not None:
            doc["context_prefix"] = context_prefix
        self._col.update_one({"_id": chunk_id}, {"$set": doc}, upsert=True)

    def delete_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> int:
        """Entfernt alle Chunks einer Mail (Re-Index / Idempotenz)."""
        query = with_account_filter({"correlation_id": correlation_id}, account_id)
        result = self._col.delete_many(query)
        return int(result.deleted_count)

    def list_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lädt alle Chunks einer Mail-Korrelation."""
        query = with_account_filter({"correlation_id": correlation_id}, account_id)
        return list(self._col.find(query))

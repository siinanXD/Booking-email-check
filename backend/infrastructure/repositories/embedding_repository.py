"""Embeddings und Vektor-Speicher (Atlas)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from backend.infrastructure.repositories.mongo import Db

logger = logging.getLogger(__name__)

VECTOR_INDEX_NAME = "embedding_vector_index"


class EmbeddingRepository:
    """Collection `embeddings` mit Metadaten für Hybrid-Suche."""

    COLLECTION = "embeddings"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("correlation_id", 1)])

    def upsert_chunk(
        self,
        chunk_id: str,
        correlation_id: str,
        text: str,
        embedding: list[float],
        intent: str | None = None,
        *,
        account_id: str | None = None,
        chunk_index: int | None = None,
        token_count: int | None = None,
        char_start: int | None = None,
        char_end: int | None = None,
        context_prefix: str | None = None,
    ) -> None:
        """Speichert einen Chunk inkl. Embedding-Vektor."""
        doc: dict[str, Any] = {
            "_id": chunk_id,
            "correlation_id": correlation_id,
            "text": text,
            "embedding": embedding,
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
        """Entfernt alle Embeddings einer Mail (Re-Index / Idempotenz)."""
        query: dict[str, Any] = {"correlation_id": correlation_id}
        if account_id:
            query["account_id"] = account_id
        result = self._col.delete_many(query)
        return int(result.deleted_count)

    def search_by_vector(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Einfache Ähnlichkeitssuche (Dot-Product auf kleinen MVP-Daten)."""
        query = filter or {}
        docs = list(self._col.find(query))
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in docs:
            emb = doc.get("embedding") or []
            if not emb:
                continue
            score = _dot(query_embedding, emb)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:limit]]

    def search_by_vector_atlas(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Nutzt Atlas $vectorSearch Aggregation Pipeline."""
        try:
            vector_search: dict[str, Any] = {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": max(limit * 10, 50),
                "limit": limit,
            }
            if filter:
                vector_search["filter"] = filter
            pipeline = [{"$vectorSearch": vector_search}]
            return list(self._col.aggregate(pipeline))
        except OperationFailure:
            logger.warning(
                "atlas_vector_search_unavailable: falling back to in-memory "
                "dot-product (correlation_id=%s, index=%s)",
                filter.get("correlation_id") if filter else "n/a",
                VECTOR_INDEX_NAME,
            )
            return self.search_by_vector(
                query_embedding,
                limit=limit,
                filter=filter,
            )


def _dot(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))

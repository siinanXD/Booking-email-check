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


def build_vector_index_definition(
    *, dimensions: int = 1536, similarity: str = "cosine"
) -> dict[str, Any]:
    """Atlas-$vectorSearch-Definition: embedding-Vektor + account_id-Filter.

    Der account_id-Filter ist zwingend — jede Suche ist mandantengefiltert
    (``{account_id: ...}``); ohne deklariertes Filterfeld scheitert
    ``$vectorSearch`` und RAG liefert nie similar_cases.
    """
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": dimensions,
                "similarity": similarity,
            },
            {"type": "filter", "path": "account_id"},
        ]
    }


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

    def search_by_vector_atlas(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Nutzt Atlas $vectorSearch.

        Bewusst KEIN In-Memory-Fallback: Wenn der Atlas-Vektorindex nicht
        verfügbar ist (DB offline, Index fehlt), wird eine Warnung geloggt und
        eine leere Liste zurückgegeben. Die ganze Collection in den RAM zu laden
        und lokal Dot-Products zu rechnen wäre ein Speicher-Risiko und ist daher
        deaktiviert. Fallähnlichkeit ist nicht-blockierend (SPEC).
        """
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
                "vektordatenbank_offline: Atlas Vector Search nicht verfügbar "
                "(index=%s) – Ähnlichkeitssuche wird übersprungen, keine "
                "lokale Fallback-Berechnung.",
                VECTOR_INDEX_NAME,
            )
            return []

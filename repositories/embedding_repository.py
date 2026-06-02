"""Embeddings und Vektor-Speicher (Atlas)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from repositories.mongo import Db


class EmbeddingRepository:
    """Collection `embeddings` mit Metadaten für Hybrid-Suche."""

    COLLECTION = "embeddings"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def upsert_chunk(
        self,
        chunk_id: str,
        correlation_id: str,
        text: str,
        embedding: list[float],
        intent: str | None = None,
    ) -> None:
        """Speichert einen Chunk inkl. Embedding-Vektor."""
        doc = {
            "_id": chunk_id,
            "correlation_id": correlation_id,
            "text": text,
            "embedding": embedding,
            "intent": intent,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._col.update_one({"_id": chunk_id}, {"$set": doc}, upsert=True)

    def search_by_vector(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Einfache Ähnlichkeitssuche (Dot-Product auf kleinen MVP-Daten)."""
        docs = list(self._col.find({}))
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in docs:
            emb = doc.get("embedding") or []
            if not emb:
                continue
            score = _dot(query_embedding, emb)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:limit]]


def _dot(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))

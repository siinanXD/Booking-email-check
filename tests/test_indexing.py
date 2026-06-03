"""Indexierung und Chunking."""

from __future__ import annotations

from unittest.mock import MagicMock

from pymongo.errors import OperationFailure

from backend.ai.services.indexing import chunk_text
from backend.infrastructure.repositories.embedding_repository import (
    VECTOR_INDEX_NAME,
    EmbeddingRepository,
    _dot,
)


def test_chunk_text_paragraphs() -> None:
    """Verify chunk text paragraphs."""
    body = "A\n\nB\n\nC\n\nD"
    chunks = chunk_text(body, max_chunks=2)
    assert len(chunks) == 2


def test_embedding_repository_search(mock_db) -> None:
    """Verify embedding repository search."""
    repo = EmbeddingRepository(mock_db)
    repo.upsert_chunk("c1", "corr-1", "hello", [1.0, 0.0], "guest_inquiry")
    repo.upsert_chunk("c2", "corr-2", "world", [0.0, 1.0], "other")
    results = repo.search_by_vector([1.0, 0.0], limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "c1"


def test_dot_product() -> None:
    """Verify dot product."""
    assert _dot([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_search_by_vector_atlas_uses_aggregate(mock_db) -> None:
    """Verify atlas search delegates to aggregate pipeline."""
    repo = EmbeddingRepository(mock_db)
    repo._col.aggregate = MagicMock(return_value=[{"_id": "c1", "text": "hello"}])
    results = repo.search_by_vector_atlas([1.0, 0.0], limit=2)
    assert len(results) == 1
    repo._col.aggregate.assert_called_once()
    pipeline = repo._col.aggregate.call_args[0][0]
    assert pipeline[0]["$vectorSearch"]["index"] == VECTOR_INDEX_NAME


def test_search_by_vector_atlas_falls_back_on_operation_failure(mock_db) -> None:
    """Verify atlas search falls back to in-memory search."""
    repo = EmbeddingRepository(mock_db)
    repo._col.aggregate = MagicMock(
        side_effect=OperationFailure("vector search unavailable")
    )
    repo.upsert_chunk("c1", "corr-1", "hello", [1.0, 0.0], "guest_inquiry")
    results = repo.search_by_vector_atlas([1.0, 0.0], limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "c1"

"""Indexierung und Chunking."""

from __future__ import annotations

from repositories.embedding_repository import EmbeddingRepository, _dot
from services.indexing import chunk_text


def test_chunk_text_paragraphs() -> None:
    body = "A\n\nB\n\nC\n\nD"
    chunks = chunk_text(body, max_chunks=2)
    assert len(chunks) == 2


def test_embedding_repository_search(mock_db) -> None:
    repo = EmbeddingRepository(mock_db)
    repo.upsert_chunk("c1", "corr-1", "hello", [1.0, 0.0], "guest_inquiry")
    repo.upsert_chunk("c2", "corr-2", "world", [0.0, 1.0], "other")
    results = repo.search_by_vector([1.0, 0.0], limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "c1"


def test_dot_product() -> None:
    assert _dot([1.0, 0.0], [1.0, 0.0]) == 1.0

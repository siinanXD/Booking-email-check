"""Similarity-Search mit Mock-Embedding."""

from __future__ import annotations

from repositories.embedding_repository import EmbeddingRepository


class MockEmbedClient:
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0] if "hello" in text else [0.0, 1.0]


def test_find_similar_cases(mock_db) -> None:
    from services.similarity_search import SimilaritySearchService

    repo = EmbeddingRepository(mock_db)
    repo.upsert_chunk("s1", "c1", "hello world", [1.0, 0.0], "guest_inquiry")
    repo.upsert_chunk("s2", "c2", "other topic", [0.0, 1.0], "other")
    svc = SimilaritySearchService(repo, MockEmbedClient())
    results = svc.find_similar_cases("hello there", limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "s1"

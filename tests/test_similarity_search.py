"""Similarity-Search mit Mock-Embedding."""

from __future__ import annotations

from unittest.mock import patch

from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository


class MockEmbedClient:
    """Test helper used by the suite."""

    def embed(self, text: str) -> list[float]:
        """Execute the operation."""
        return [1.0, 0.0] if "hello" in text else [0.0, 1.0]


def test_find_similar_cases(mock_db) -> None:
    """Verify find similar cases."""
    from backend.ai.services.similarity_search import SimilaritySearchService

    repo = EmbeddingRepository(mock_db)
    repo.upsert_chunk("s1", "c1", "hello world", [1.0, 0.0], "guest_inquiry")
    repo.upsert_chunk("s2", "c2", "other topic", [0.0, 1.0], "other")
    svc = SimilaritySearchService(repo, MockEmbedClient())
    results = svc.find_similar_cases("hello there", limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "s1"


def test_find_similar_cases_uses_atlas_when_enabled(mock_db) -> None:
    """Verify atlas backend is selected when use_atlas=True."""
    from backend.ai.services.similarity_search import SimilaritySearchService

    repo = EmbeddingRepository(mock_db)
    with (
        patch.object(
            repo,
            "search_by_vector_atlas",
            return_value=[{"_id": "atlas-1"}],
        ) as atlas_mock,
        patch.object(
            repo,
            "search_by_vector",
            return_value=[{"_id": "memory-1"}],
        ) as memory_mock,
    ):
        svc = SimilaritySearchService(repo, MockEmbedClient(), use_atlas=True)
        results = svc.find_similar_cases("hello there", limit=1)
        atlas_mock.assert_called_once()
        memory_mock.assert_not_called()
        assert results[0]["_id"] == "atlas-1"


def test_find_similar_cases_uses_memory_when_atlas_disabled(mock_db) -> None:
    """Verify in-memory backend is selected when use_atlas=False."""
    from backend.ai.services.similarity_search import SimilaritySearchService

    repo = EmbeddingRepository(mock_db)
    with (
        patch.object(
            repo,
            "search_by_vector_atlas",
            return_value=[{"_id": "atlas-1"}],
        ) as atlas_mock,
        patch.object(
            repo,
            "search_by_vector",
            return_value=[{"_id": "memory-1"}],
        ) as memory_mock,
    ):
        svc = SimilaritySearchService(repo, MockEmbedClient(), use_atlas=False)
        results = svc.find_similar_cases("hello there", limit=1)
        memory_mock.assert_called_once()
        atlas_mock.assert_not_called()
        assert results[0]["_id"] == "memory-1"

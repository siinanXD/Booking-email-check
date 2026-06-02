"""Fallähnlichkeit über Vektorindex."""

from __future__ import annotations

from repositories.embedding_repository import EmbeddingRepository
from services.indexing import EmbeddingClient


class SimilaritySearchService:
    """Optionale Ähnlichkeitssuche – nicht blockierend für Antwortpfad."""

    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embed_client: EmbeddingClient,
    ) -> None:
        self._repo = embedding_repo
        self._embed = embed_client

    def find_similar_cases(
        self,
        query_text: str,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """Sucht ähnliche historische Fälle."""
        vector = self._embed.embed(query_text)
        return self._repo.search_by_vector(vector, limit=limit)

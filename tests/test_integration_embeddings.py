"""Integration: Embedding upsert + In-Memory-Vektorsuche (live MongoDB, optional)."""

from __future__ import annotations

import os

import pytest

from backend.core.config.settings import Settings
from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository
from backend.infrastructure.repositories.mongo import get_database


@pytest.mark.integration
def test_embedding_upsert_and_search_by_vector() -> None:
    """Speichert zwei Chunks und findet den ähnlicheren per Dot-Product."""
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI not set")
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": uri,
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
        }
    )
    db = get_database(settings)
    repo = EmbeddingRepository(db)
    account_id = "integration-embed-test"
    corr_a = "corr-embed-a"
    corr_b = "corr-embed-b"
    try:
        repo.upsert_chunk(
            "chunk-a",
            corr_a,
            "Stornierung Buchung AB100",
            [1.0, 0.0, 0.0],
            intent="cancellation",
            account_id=account_id,
        )
        repo.upsert_chunk(
            "chunk-b",
            corr_b,
            "Neue Reservierung Gast Anreise",
            [0.0, 1.0, 0.0],
            intent="new_booking",
            account_id=account_id,
        )
        hits = repo.search_by_vector(
            [0.95, 0.05, 0.0],
            limit=2,
            filter={"account_id": account_id},
        )
        assert len(hits) >= 1
        assert hits[0]["correlation_id"] == corr_a
    finally:
        repo._col.delete_many({"account_id": account_id})

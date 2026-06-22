"""Indexierung und Chunking."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from pymongo.errors import OperationFailure

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.services.indexing import IndexingService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.repositories.chunk_repository import ChunkRepository
from backend.infrastructure.repositories.embedding_repository import (
    VECTOR_INDEX_NAME,
    EmbeddingRepository,
)


class _FixedEmbed:
    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def test_search_by_vector_atlas_uses_aggregate(mock_db) -> None:
    """Verify atlas search delegates to aggregate pipeline."""
    repo = EmbeddingRepository(mock_db)
    with patch.object(
        repo._col,
        "aggregate",
        return_value=[{"_id": "c1", "text": "hello"}],
    ) as aggregate_mock:
        results = repo.search_by_vector_atlas([1.0, 0.0], limit=2)
        assert len(results) == 1
        aggregate_mock.assert_called_once()
        pipeline = aggregate_mock.call_args[0][0]
        assert pipeline[0]["$vectorSearch"]["index"] == VECTOR_INDEX_NAME


def test_search_by_vector_atlas_returns_empty_when_offline(
    mock_db,
    caplog,
) -> None:
    """Atlas offline → leere Liste, KEIN In-Memory-Fallback, Warnung im Log."""
    import logging

    repo = EmbeddingRepository(mock_db)
    repo.upsert_chunk("c1", "corr-1", "hello", [1.0, 0.0], "guest_inquiry")
    with (
        patch.object(
            repo._col,
            "aggregate",
            side_effect=OperationFailure("vector search unavailable"),
        ),
        caplog.at_level(logging.WARNING),
    ):
        results = repo.search_by_vector_atlas(
            [1.0, 0.0],
            limit=1,
            filter={"correlation_id": "corr-1"},
        )
    assert results == []
    assert any("vektordatenbank_offline" in r.message for r in caplog.records)


def test_index_async_stores_semantic_chunk_metadata(mock_db) -> None:
    """Live-Index nutzt semantic_chunk: Kontext-Prefix + Metadaten landen im Doc."""
    emb_repo = EmbeddingRepository(mock_db)
    chunk_repo = ChunkRepository(mock_db)
    svc = IndexingService(emb_repo, _FixedEmbed(), chunk_repo)
    ext = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Ferienhaus Nord",
        booking_number="AB123",
    )
    asyncio.run(
        svc._index_async(
            "corr-1",
            "Hallo, wir möchten gerne buchen.",
            ext,
            "acc-1",
            subject="Neue Buchung",
        )
    )
    docs = list(emb_repo._col.find({"correlation_id": "corr-1"}))
    assert docs, "kein Embedding gespeichert"
    doc = docs[0]
    assert doc["_id"] == "corr-1:0"
    assert doc["chunk_index"] == 0
    assert doc["account_id"] == "acc-1"
    assert doc["intent"] == "new_booking"
    assert doc["embedding"] == [0.1, 0.2, 0.3]
    # Kontext-Prefix enthält Unterkunft + Buchungsnummer (verbessert Embedding).
    assert "Ferienhaus Nord" in doc["context_prefix"]
    assert "AB123" in doc["context_prefix"]
    assert doc["token_count"] > 0


def test_index_async_is_idempotent_on_reindex(mock_db) -> None:
    """Re-Index ersetzt alte Chunks vollständig — keine Waisen bei weniger Chunks."""
    emb_repo = EmbeddingRepository(mock_db)
    svc = IndexingService(emb_repo, _FixedEmbed(), max_chunk_tokens=40)
    long_body = "\n\n".join(f"Absatz {i} mit etwas Text " * 20 for i in range(6))
    asyncio.run(svc._index_async("corr-x", long_body, None, "acc-1"))
    assert emb_repo._col.count_documents({"correlation_id": "corr-x"}) > 1
    asyncio.run(svc._index_async("corr-x", "kurz", None, "acc-1"))
    assert emb_repo._col.count_documents({"correlation_id": "corr-x"}) == 1


def test_purge_removes_embeddings_and_chunks(mock_db) -> None:
    """purge() entfernt Embeddings UND Chunks einer Mail (Nicht-Buchungs-Cleanup)."""
    emb_repo = EmbeddingRepository(mock_db)
    chunk_repo = ChunkRepository(mock_db)
    svc = IndexingService(emb_repo, _FixedEmbed(), chunk_repo)
    emb_repo.upsert_chunk("corr-p:0", "corr-p", "txt", [0.1], "other", account_id="a1")
    chunk_repo.upsert_chunk("corr-p:0", "corr-p", "txt", "other", account_id="a1")
    removed = svc.purge("corr-p", account_id="a1")
    assert removed == 1
    assert emb_repo._col.count_documents({"correlation_id": "corr-p"}) == 0
    assert chunk_repo._col.count_documents({"correlation_id": "corr-p"}) == 0


def test_index_async_alerts_on_failure(mock_db) -> None:
    """Verify async indexing emits alert with indexing: prefix on failure."""

    class FailingEmbed:
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("embed failed")

    alerts = MagicMock(spec=AlertService)
    repo = EmbeddingRepository(mock_db)
    svc = IndexingService(repo, FailingEmbed(), alerts=alerts)
    asyncio.run(svc._index_async("corr-fail", "hello world", None))
    alerts.check_extraction_failure.assert_called_once()
    args = alerts.check_extraction_failure.call_args[0]
    assert args[0] == "corr-fail"
    assert args[1].startswith("indexing:")


def test_validate_indexes_only_booking_relevant(monkeypatch) -> None:
    """Validate-Node indexiert nur buchungsrelevante Mails (Korpus-Qualität)."""
    from datetime import UTC, datetime

    from backend.ai.domain.booking.extraction import BookingExtraction
    from backend.ai.domain.booking.taxonomy import BookingIntent
    from backend.ai.workflows.nodes import pipeline as pipeline_mod
    from backend.ai.workflows.nodes.pipeline import WorkflowNodes
    from backend.core.models.email import StoredEmail

    indexing = MagicMock()
    validation = MagicMock()
    validation.validate.return_value = MagicMock(valid=True, errors=[])
    nodes = WorkflowNodes(
        ingestion=MagicMock(),
        classification=MagicMock(),
        extraction=MagicMock(),
        validation=validation,
        retrieval=MagicMock(),
        response_gen=MagicMock(),
        email_repo=MagicMock(),
        extraction_repo=MagicMock(),
        indexing=indexing,
        alerts=None,
        review_repo=None,
        notification_service=None,
    )
    email = StoredEmail(
        message_id="m-idx",
        from_address="bookings@beds24.com",
        subject="Buchung",
        body_text="Details",
        received_at=datetime.now(UTC),
        correlation_id="corr-idx",
        account_id="acc-1",
    )
    ext = BookingExtraction(intent=BookingIntent.OTHER)
    state = {"email": email, "extraction": ext}

    monkeypatch.setattr(pipeline_mod, "is_booking_relevant", lambda e, x: True)
    nodes.validate(state)
    assert indexing.schedule_index.called

    indexing.reset_mock()
    monkeypatch.setattr(pipeline_mod, "is_booking_relevant", lambda e, x: False)
    nodes.validate(state)
    assert not indexing.schedule_index.called

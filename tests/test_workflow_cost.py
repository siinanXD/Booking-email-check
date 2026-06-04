"""Workflow cost tracking tests."""

from __future__ import annotations

from backend.infrastructure.observability.mail_cost import MailCostTracker


def test_workflow_finalize_cost_after_spam_discard(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
    booking_emails,
) -> None:
    """Spam-Verwurf: MailCostTracker.finalize trotzdem am Laufende."""
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )
    from tests.test_workflow import _build_workflow

    finalized: list[str] = []

    class _RecordingTracker(MailCostTracker):
        def finalize(
            self, correlation_id: str, *, account_id: str | None = None
        ) -> float:
            finalized.append(correlation_id)
            return super().finalize(correlation_id)

    tracker = _RecordingTracker(cost_per_1k_tokens_usd=0.002)
    payload = booking_emails[1]
    wf = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        EmbeddingRepository(mock_db),
        mail_cost=tracker,
    )
    wf.run(payload, thread_id="thread-spam-cost")
    assert len(finalized) == 1
    assert finalized[0] == payload.correlation_id

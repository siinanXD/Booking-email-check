"""LangGraph-Workflow mit Mock-LLM."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import IncomingEmail, ProcessingState
from observability.mail_cost import MailCostTracker
from services.classification import ClassificationService
from services.extraction import ExtractionService
from services.grounding import GroundingService
from services.indexing import IndexingService
from services.response_generation import ResponseGenerationService
from services.retrieval import RetrievalService
from services.validation import ValidationService
from tests.mocks import MockLLM
from workflows.email_workflow import EmailWorkflow


class _MockEmbed:
    """Minimaler Embedding-Stub für Tests."""

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.5]


def _build_workflow(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    embedding_repo,
    mail_cost: MailCostTracker | None = None,
) -> EmailWorkflow:
    llm = MockLLM()
    retrieval = RetrievalService(entity_repo, email_repo)
    indexing = IndexingService(embedding_repo, _MockEmbed())  # type: ignore[arg-type]
    classify = ClassificationService(llm, "gpt-4o-mini", mail_cost=mail_cost)
    extract = ExtractionService(llm, "gpt-4o-mini", mail_cost=mail_cost)
    return EmailWorkflow(
        ingestion=ingestion_service,
        classification=classify,
        extraction=extract,
        validation=ValidationService(),
        retrieval=retrieval,
        response_gen=ResponseGenerationService(
            llm,
            "gpt-4o",
            retrieval,
            GroundingService(),
            mail_cost=mail_cost,
        ),
        email_repo=email_repo,
        extraction_repo=extraction_repo,
        indexing=indexing,
        mail_cost=mail_cost,
    )


def test_workflow_stops_with_review_pending(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    from repositories.embedding_repository import EmbeddingRepository

    payload = IncomingEmail(
        message_id="wf-001",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Bitte stornieren Sie die Reservierung AB200.",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    wf = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        EmbeddingRepository(mock_db),
    )
    result = wf.run(payload, thread_id="thread-wf-001")
    assert "draft" in result
    assert result.get("review") is None
    stored = extraction_repo.get_by_correlation_id(payload.correlation_id)
    assert stored is not None
    assert stored.booking_number == "AB200"


def test_workflow_persists_processing_state(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    from repositories.embedding_repository import EmbeddingRepository

    payload = IncomingEmail(
        message_id="wf-002",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Stornierung AB200 bitte.",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    wf = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        EmbeddingRepository(mock_db),
    )
    wf.run(payload, thread_id="thread-wf-002")
    email = email_repo.get_by_message_id("wf-002")
    assert email is not None
    assert email.processing_state in (
        ProcessingState.DRAFTED,
        ProcessingState.PENDING_REVIEW,
    )


def test_workflow_finalize_cost_after_spam_discard(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
    booking_emails,
) -> None:
    """Spam-Verwurf: MailCostTracker.finalize trotzdem am Laufende."""
    from repositories.embedding_repository import EmbeddingRepository

    finalized: list[str] = []

    class _RecordingTracker(MailCostTracker):
        def finalize(self, correlation_id: str) -> float:
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

"""LangGraph-Workflow mit Mock-LLM."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.services.classification import ClassificationService
from backend.ai.services.extraction import ExtractionService
from backend.ai.services.grounding import GroundingService
from backend.ai.services.indexing import IndexingService
from backend.ai.services.response_generation import ResponseGenerationService
from backend.ai.services.retrieval import RetrievalService
from backend.ai.services.validation import ValidationService
from backend.ai.workflows.email_workflow import EmailWorkflow
from backend.core.models.email import IncomingEmail, ProcessingState
from backend.infrastructure.observability.mail_cost import MailCostTracker
from tests.mocks import MockLLM


class _MockEmbed:
    """Minimaler Embedding-Stub für Tests."""

    def embed(self, text: str) -> list[float]:
        """Execute the operation."""
        return [1.0, 0.5]


def _build_workflow(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    embedding_repo,
    mail_cost: MailCostTracker | None = None,
    review_repo=None,
    tenant_workflow_repo=None,
) -> EmailWorkflow:
    from backend.ai.services.tenant_workflow_runtime import (
        TenantWorkflowExecutor,
        WorkflowRouter,
    )

    llm = MockLLM()
    retrieval = RetrievalService(entity_repo, email_repo)
    indexing = IndexingService(embedding_repo, _MockEmbed())  # type: ignore[arg-type]
    classify = ClassificationService(llm, "gpt-4o-mini", mail_cost=mail_cost)
    extract = ExtractionService(llm, "gpt-4o-mini", mail_cost=mail_cost)
    workflow_router = (
        WorkflowRouter(tenant_workflow_repo) if tenant_workflow_repo else None
    )
    tenant_executor = TenantWorkflowExecutor(
        llm,
        classify_model="gpt-4o-mini",
        extract_model="gpt-4o-mini",
    )
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
        review_repo=review_repo,
        workflow_router=workflow_router,
        tenant_workflow_executor=tenant_executor,
        tenant_workflow_repo=tenant_workflow_repo,
    )


def test_workflow_stops_with_review_pending(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    """Verify workflow stops with review pending."""
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )

    payload = IncomingEmail(
        message_id="wf-001",
        from_address="guest@airbnb.com",
        subject="Stornierung AB200",
        body_text="Bitte stornieren Sie die Reservierung AB200.",
        received_at=datetime.now(UTC),
        platform="airbnb",
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    wf = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        EmbeddingRepository(mock_db),
        review_repo=ReviewRepository(mock_db),
    )
    result = wf.run(payload, thread_id="thread-wf-001")
    assert "draft" in result
    review = result.get("review")
    assert review is not None
    assert review.status == "pending"
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
    """Verify workflow persists processing state."""
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )

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


def test_resume_after_approval_persists_approved_state(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    """Verify approval resume persists the approved processing state."""
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )

    payload = IncomingEmail(
        message_id="wf-approve-001",
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
    wf.run(payload, thread_id=payload.correlation_id)
    result = wf.resume_after_approval(
        payload.correlation_id,
        approved_body="Freigegebener Text",
    )

    email = email_repo.get_by_message_id("wf-approve-001")
    assert email is not None
    assert email.processing_state == ProcessingState.APPROVED
    assert result["review"].status == "approved"
    assert result["review"].approved_body == "Freigegebener Text"


def test_resume_after_rejection_persists_rejected_state(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    """Verify rejection resume persists rejected processing state."""
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

    review_repo = ReviewRepository(mock_db)
    payload = IncomingEmail(
        message_id="wf-reject-001",
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
        review_repo=review_repo,
    )
    wf.run(payload, thread_id=payload.correlation_id)
    result = wf.reject_after_review(
        payload.correlation_id,
        reason="Inaccurate draft",
    )

    email = email_repo.get_by_message_id("wf-reject-001")
    assert email is not None
    assert email.processing_state == ProcessingState.REJECTED
    assert result["review"].status == "rejected"
    record = review_repo.get(payload.correlation_id)
    assert record is not None
    assert record.review_status == "rejected"
    assert record.reviewer_note == "Inaccurate draft"


def test_workflow_skips_classify_llm_on_unknown_discard(
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    """Verworfene Fremdmail: kein classify/extract-LLM-Aufruf."""
    from backend.ai.services.ingestion import IngestionService
    from backend.ai.services.triage import TriageService
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )

    class _CountingLLM(MockLLM):
        def __init__(self) -> None:
            self.complete_calls = 0

        def complete(self, prompt, model, *, temperature=None):
            self.complete_calls += 1
            return super().complete(prompt, model, temperature=temperature)

    counting = _CountingLLM()
    ingestion = IngestionService(
        email_repo,
        TriageService(triage_llm_enabled=False),
    )
    llm = counting
    embedding_repo = EmbeddingRepository(mock_db)
    retrieval = RetrievalService(entity_repo, email_repo)
    indexing = IndexingService(embedding_repo, _MockEmbed())  # type: ignore[arg-type]
    classify = ClassificationService(llm, "gpt-4o-mini")
    extract = ExtractionService(llm, "gpt-4o-mini")
    wf = EmailWorkflow(
        ingestion=ingestion,
        classification=classify,
        extraction=extract,
        validation=ValidationService(),
        retrieval=retrieval,
        response_gen=ResponseGenerationService(
            llm,
            "gpt-4o",
            retrieval,
            GroundingService(),
        ),
        email_repo=email_repo,
        extraction_repo=extraction_repo,
        indexing=indexing,
    )
    payload = IncomingEmail(
        message_id="wf-unknown-discard",
        from_address="unknown@random.org",
        subject="Hello",
        body_text="Generic inquiry",
        received_at=datetime.now(UTC),
    )
    wf.run(payload, thread_id=payload.correlation_id)
    assert counting.complete_calls == 0

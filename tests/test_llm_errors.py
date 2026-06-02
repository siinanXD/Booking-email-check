"""Robustheit bei LLM-/Netzwerkfehlern."""

from __future__ import annotations

from datetime import UTC, datetime

from models.email import StoredEmail
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from services.classification import ClassificationService
from services.extraction import ExtractionService
from services.grounding import GroundingService
from services.llm_types import LLMCompletion
from services.response_generation import ResponseGenerationService
from services.retrieval import RetrievalService


class FailingLLM:
    def complete(self, prompt: str, model: str) -> LLMCompletion:
        raise ConnectionError("simulated network failure")


def test_classify_returns_other_on_llm_failure() -> None:
    email = StoredEmail(
        message_id="fail-cls",
        from_address="g@airbnb.com",
        subject="Test",
        body_text="Body",
        received_at=datetime.now(UTC),
    )
    assert (
        ClassificationService(FailingLLM(), "gpt-4o-mini").classify(email)
        == BookingIntent.OTHER
    )


def test_extract_returns_low_confidence_on_llm_failure() -> None:
    email = StoredEmail(
        message_id="fail-ext",
        from_address="g@airbnb.com",
        subject="Test",
        body_text="Body",
        received_at=datetime.now(UTC),
    )
    ext = ExtractionService(FailingLLM(), "gpt-4o-mini").extract(email)
    assert ext.confidence == 0.0


def test_generate_draft_fallback_on_llm_failure(
    entity_repo,
    email_repo,
) -> None:
    email = StoredEmail(
        message_id="fail-draft",
        from_address="g@test.com",
        subject="Test",
        body_text="Body",
        received_at=datetime.now(UTC),
        correlation_id="corr-fail-draft",
    )
    retrieval = RetrievalService(entity_repo, email_repo)
    draft = ResponseGenerationService(
        FailingLLM(),
        "gpt-4o",
        retrieval,
        GroundingService(),
    ).generate_draft(email, BookingExtraction())
    assert "fehlgeschlagen" in draft.body.lower()
    assert draft.grounding_ok is False

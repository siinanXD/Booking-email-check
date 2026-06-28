"""LangGraph State für den E-Mail-Workflow."""

from __future__ import annotations

from typing import TypedDict

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.domain.booking.triage import TriageResult
from backend.ai.services.retrieval import RetrievalHits
from backend.core.models.email import StoredEmail
from backend.core.models.response import GeneratedResponse, ReviewStatus


class EmailWorkflowState(TypedDict, total=False):
    """Zustand durch alle Pipeline-Nodes."""

    email: StoredEmail
    ingest_duplicate: bool
    ingest_discarded: bool
    triage: TriageResult
    intent: BookingIntent
    extraction: BookingExtraction
    validation_errors: list[str]
    retrieval: RetrievalHits
    draft: GeneratedResponse
    review: ReviewStatus
    grounding_flag: bool
    auto_approve: bool
    auto_approve_body: str
    error: str
    workflow_id: str
    workflow_slug: str
    custom_extraction: dict[str, object]

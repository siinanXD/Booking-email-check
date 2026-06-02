"""LangGraph State für den E-Mail-Workflow."""

from __future__ import annotations

from typing import TypedDict

from models.email import StoredEmail
from models.response import GeneratedResponse, ReviewStatus
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from schemas.booking.triage import TriageResult
from services.retrieval import RetrievalHits


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
    error: str

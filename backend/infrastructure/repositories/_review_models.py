"""ReviewRecord-Modell und Konvertierungshelfer."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.core.models.response import ReviewStatus


class ReviewRecord(BaseModel):
    """Gespeicherter Review-Stand für die Web-API."""

    correlation_id: str
    message_id: str
    draft_body: str = ""
    grounding_flag: bool = False
    review_status: str = "pending"
    reviewer_note: str | None = None
    approved_body: str | None = None
    intent: str | None = None
    # Klassifizierungs-/Grounding-Detail für „Warum diese Einstufung?".
    confidence: float = 1.0
    signals: list[str] = Field(default_factory=list)
    grounding_span: str | None = None
    # Eskalation + Auto-Freigabe (inkl. Undo-Fenster).
    escalated: bool = False
    auto_approved: bool = False
    auto_approved_at: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def record_to_status(record: ReviewRecord) -> ReviewStatus:
    return ReviewStatus(
        correlation_id=record.correlation_id,
        status=record.review_status,
        reviewer_note=record.reviewer_note,
        approved_body=record.approved_body,
        escalated=record.escalated,
    )

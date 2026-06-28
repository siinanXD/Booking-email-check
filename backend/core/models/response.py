"""Antwort- und Review-Modelle."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class GeneratedResponse(BaseModel):
    """Vom System erzeugter Antwortentwurf (noch nicht versendet)."""

    correlation_id: str
    body: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    grounding_ok: bool = True
    # Konfidenz 0–1 (aus Grounding); steuert die Auto-Freigabe und den
    # Konfidenz-Ring der „Warum diese Einstufung?"-Ansicht.
    confidence: float = 1.0
    # Erkannte Grounding-Signale (z. B. "booking_ref", "guest_name", "date").
    grounding_signals: list[str] = Field(default_factory=list)
    # Zitierte Belegstelle aus der Mail (Highlight in der UI).
    grounding_span: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    # Langfuse-Trace der Draft-Generation; ermöglicht später Review-Scores auf
    # genau diesen Trace (überlebt den Human-Interrupt im Workflow-State).
    langfuse_trace_id: str | None = None


class ReviewStatus(BaseModel):
    """Status der menschlichen Freigabe."""

    correlation_id: str
    status: str = "pending"  # pending | approved | rejected
    reviewer_note: str | None = None
    approved_body: str | None = None
    # Priorisiert an einen Menschen (Beschwerde / niedrige Konfidenz).
    escalated: bool = False

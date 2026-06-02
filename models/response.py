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
    created_at: datetime = Field(default_factory=_utc_now)


class ReviewStatus(BaseModel):
    """Status der menschlichen Freigabe."""

    correlation_id: str
    status: str = "pending"  # pending | approved | rejected
    reviewer_note: str | None = None
    approved_body: str | None = None

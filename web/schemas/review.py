"""Review-API-Schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ReviewApproveRequest(BaseModel):
    """Freigabe-Body."""

    correlation_id: str
    approved_body: str | None = None


class ReviewRejectRequest(BaseModel):
    """Ablehnungs-Body."""

    correlation_id: str
    reason: str = ""


class ReviewQueueItem(BaseModel):
    """Eintrag in der Review-Warteschlange."""

    correlation_id: str
    message_id: str
    subject: str = ""
    from_address: str = ""
    intent: str | None = None
    draft_body: str = ""
    grounding_flag: bool = False
    review_status: str = "pending"
    received_at: str | None = None


class ReviewQueueResponse(BaseModel):
    """Liste ausstehender Reviews."""

    items: list[ReviewQueueItem]
    total: int

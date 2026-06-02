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

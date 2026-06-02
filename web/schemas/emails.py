"""E-Mail-API-Schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EmailListItem(BaseModel):
    """Kompakte Mail-Zeile."""

    correlation_id: str
    message_id: str
    subject: str = ""
    from_address: str = ""
    received_at: str | None = None
    platform: str | None = None
    intent: str | None = None
    booking_number: str | None = None
    processing_state: str = ""
    review_status: str | None = None
    grounding_flag: bool = False


class EmailListResponse(BaseModel):
    """Paginierte Liste."""

    items: list[EmailListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pages: int = 0


class EmailDetail(BaseModel):
    """Vollständiges Mail-Detail."""

    correlation_id: str
    message_id: str
    subject: str = ""
    from_address: str = ""
    to_addresses: list[str] = Field(default_factory=list)
    body_text: str = ""
    received_at: str | None = None
    platform: str | None = None
    intent: str | None = None
    booking_number: str | None = None
    processing_state: str = ""
    review_status: str | None = None
    grounding_flag: bool = False
    draft_body: str = ""
    extraction: dict[str, Any] | None = None
    approved_body: str | None = None

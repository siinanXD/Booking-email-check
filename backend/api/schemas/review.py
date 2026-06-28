"""Review-API-Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewApproveRequest(BaseModel):
    """Freigabe-Body."""

    correlation_id: str
    approved_body: str | None = None


class ReviewRejectRequest(BaseModel):
    """Ablehnungs-Body."""

    correlation_id: str
    reason: str = ""


class ReviewCompleteRequest(BaseModel):
    """Abschluss nach Freigabe."""

    correlation_id: str


class ReviewUndoRequest(BaseModel):
    """Macht eine Auto-Freigabe innerhalb des Undo-Fensters rückgängig."""

    correlation_id: str


class ReviewTranslateRequest(BaseModel):
    """Übersetzt den aktuellen Entwurf in die Zielsprache (DE/EN-Umschalter)."""

    correlation_id: str
    target_language: str = "en"
    draft_body: str | None = None


class ReviewTranslateResponse(BaseModel):
    """Übersetzter Entwurf."""

    correlation_id: str
    target_language: str
    translated_body: str


class ReviewBulkApproveRequest(BaseModel):
    """Sammel-Freigabe mehrerer Entwürfe (Review-Shortcuts/Checkboxen)."""

    correlation_ids: list[str]


class ReviewBulkApproveItem(BaseModel):
    """Ergebnis einer einzelnen Freigabe in der Sammel-Aktion."""

    correlation_id: str
    status: str
    error: str | None = None


class ReviewBulkApproveResponse(BaseModel):
    """Aggregiertes Ergebnis der Sammel-Freigabe."""

    approved: int = 0
    failed: int = 0
    items: list[ReviewBulkApproveItem]


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
    confidence: float | None = None
    escalated: bool = False
    signals: list[str] = Field(default_factory=list)
    grounding_span: str | None = None
    source_flags: list[str] = Field(default_factory=list)


class ReviewQueueResponse(BaseModel):
    """Liste ausstehender Reviews."""

    items: list[ReviewQueueItem]
    total: int

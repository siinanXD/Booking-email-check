"""E-Mail-Datenmodelle für Ingestion und Persistenz."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ProcessingState(StrEnum):
    """Verarbeitungsstatus einer eingegangenen Mail."""

    RECEIVED = "received"
    TRIAGED = "triaged"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    RETRIEVED = "retrieved"
    DRAFTED = "drafted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISCARDED = "discarded"


class IncomingEmail(BaseModel):
    """Normalisierte eingehende Mail vor Persistenz."""

    message_id: str
    from_address: str
    to_addresses: list[str] = Field(default_factory=list)
    subject: str = ""
    body_text: str = ""
    body_html: str | None = None
    received_at: datetime
    in_reply_to: str | None = None
    references: list[str] = Field(default_factory=list)
    platform: str | None = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))

    def thread_ids(self) -> list[str]:
        """Kombinierte Thread-Referenzen für Dedup/Rekonstruktion."""
        ids: list[str] = []
        if self.in_reply_to:
            ids.append(self.in_reply_to)
        ids.extend(self.references)
        return ids


class StoredEmail(IncomingEmail):
    """Persistierte Mail inkl. Triage und Verarbeitungsstatus."""

    triage_outcome: str | None = None
    processing_state: ProcessingState = ProcessingState.RECEIVED
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        """Serialisierung für MongoDB."""
        data = self.model_dump(mode="json")
        data["_id"] = self.message_id
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> StoredEmail:
        """Deserialisierung aus MongoDB-Dokument."""
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc and "message_id" not in payload:
            payload["message_id"] = doc["_id"]
        return cls.model_validate(payload)

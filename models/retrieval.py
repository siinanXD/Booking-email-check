"""Retrieval-Ergebnis-Modelle."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.email import StoredEmail
from models.entities import Guest, Reservation


class RetrievalResult(BaseModel):
    """Zusammenfassung eines Metadaten-Retrievals."""

    guest: Guest | None = None
    reservations: list[Reservation] = Field(default_factory=list)
    thread_emails: list[StoredEmail] = Field(default_factory=list)
    similar_cases: list[dict[str, object]] = Field(default_factory=list)

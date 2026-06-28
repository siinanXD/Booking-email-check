"""DTOs für die globale Suche (Topbar-Overlay)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """Ein einzelner Treffer in einer Ergebnisgruppe."""

    id: str
    title: str
    subtitle: str = ""
    href: str


class SearchResponse(BaseModel):
    """Gruppierte Treffer über Buchungen, Unterkünfte und Mails."""

    bookings: list[SearchHit] = Field(default_factory=list)
    properties: list[SearchHit] = Field(default_factory=list)
    mails: list[SearchHit] = Field(default_factory=list)

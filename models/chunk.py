"""Chunk- und Embedding-Modelle."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Textsegment einer Mail für Indexierung."""

    chunk_id: str
    correlation_id: str
    text: str
    intent: str | None = None


class Embedding(BaseModel):
    """Embedding-Vektor zu einem Chunk."""

    chunk_id: str
    correlation_id: str
    vector: list[float] = Field(default_factory=list)
    model: str = "text-embedding-3-small"

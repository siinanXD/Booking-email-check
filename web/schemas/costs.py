"""Kosten-API-Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CostSeriesPoint(BaseModel):
    """Ein Punkt in der Kosten-Zeitreihe."""

    date: str
    cost_usd: float = 0.0
    total_tokens: int = 0
    mail_count: int = 0


class CostsResponse(BaseModel):
    """Kosten-Aggregation."""

    series: list[CostSeriesPoint] = Field(default_factory=list)
    total_usd: float = 0.0

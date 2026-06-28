"""DTOs für das Admin-Datenfluss-Board (Funnel, Entscheidungen, Stuck-Liste)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FunnelStage(BaseModel):
    """Eine Pipeline-Stufe mit Anzahl."""

    state: str
    label: str
    count: int


class PipelineFunnel(BaseModel):
    """Funnel über alle ProcessingStates."""

    states: list[FunnelStage] = Field(default_factory=list)
    total: int = 0


class ConfidenceBucket(BaseModel):
    bucket: str
    count: int


class SourceFlagCount(BaseModel):
    flag: str
    count: int


class GroundingSplit(BaseModel):
    ok: int = 0
    fail: int = 0


class DecisionBreakdown(BaseModel):
    """Entscheidungs-Kennzahlen im Zeitfenster."""

    auto_approved: int = 0
    human_approved: int = 0
    escalated: int = 0
    rejected: int = 0
    pending: int = 0
    confidence_buckets: list[ConfidenceBucket] = Field(default_factory=list)
    grounding: GroundingSplit = Field(default_factory=GroundingSplit)
    top_source_flags: list[SourceFlagCount] = Field(default_factory=list)


class AdminPipelineResponse(BaseModel):
    """Funnel + Entscheidungen für einen Zeitraum."""

    days: int
    funnel: PipelineFunnel
    decisions: DecisionBreakdown


class AdminStuckItem(BaseModel):
    """Eine steckengebliebene oder verworfene Mail."""

    correlation_id: str
    account_id: str | None = None
    tenant: str | None = None
    subject: str = ""
    processing_state: str
    updated_at: str | None = None
    age_hours: int = 0
    reason: str | None = None


class AdminStuckResponse(BaseModel):
    """Liste steckengebliebener/verworfener Mails."""

    kind: str
    items: list[AdminStuckItem] = Field(default_factory=list)
    total: int = 0

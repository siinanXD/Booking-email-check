"""Admin-Datenfluss: Pipeline-Funnel + Entscheidungs-Aggregation (plattformweit)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.api.schemas.admin_pipeline import (
    AdminPipelineResponse,
    ConfidenceBucket,
    DecisionBreakdown,
    FunnelStage,
    GroundingSplit,
    PipelineFunnel,
    SourceFlagCount,
)
from backend.core.config.factory import AppContext
from backend.core.models.email import ProcessingState

_STAGE_LABELS: dict[str, str] = {
    "received": "Empfangen",
    "triaged": "Triagiert",
    "classified": "Klassifiziert",
    "extracted": "Extrahiert",
    "validated": "Validiert",
    "retrieved": "Kontext geladen",
    "drafted": "Entwurf",
    "pending_review": "Review offen",
    "approved": "Freigegeben",
    "rejected": "Abgelehnt",
    "discarded": "Verworfen",
}


def admin_pipeline(ctx: AppContext, *, days: int) -> AdminPipelineResponse:
    """Funnel über ProcessingStates + Entscheidungs-Kennzahlen im Zeitfenster."""
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    counts = ctx.email_repo.count_by_all_states(since, account_id=None)
    stages = [
        FunnelStage(
            state=state.value,
            label=_STAGE_LABELS.get(state.value, state.value),
            count=int(counts.get(state.value, 0)),
        )
        for state in ProcessingState
    ]
    funnel = PipelineFunnel(states=stages, total=int(counts.get("received", 0)))

    raw = ctx.review_repo.decision_breakdown(since, account_id=None)
    decisions = DecisionBreakdown(
        auto_approved=raw["auto_approved"],
        human_approved=raw["human_approved"],
        escalated=raw["escalated"],
        rejected=raw["rejected"],
        pending=raw["pending"],
        confidence_buckets=[ConfidenceBucket(**b) for b in raw["confidence_buckets"]],
        grounding=GroundingSplit(**raw["grounding"]),
        top_source_flags=[SourceFlagCount(**f) for f in raw["top_source_flags"]],
    )
    return AdminPipelineResponse(days=days, funnel=funnel, decisions=decisions)

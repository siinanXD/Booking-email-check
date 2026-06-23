"""Edit-Distanz zwischen Draft und freigegebener Antwort."""

from __future__ import annotations

import difflib

from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer


class ReviewFeedbackTracker:
    """Misst menschliche Korrekturen am Antwortentwurf."""

    def __init__(self, alerts: AlertService | None = None) -> None:
        self._alerts = alerts

    def record(
        self,
        correlation_id: str,
        draft_body: str,
        approved_body: str,
        tracer: LangfuseTracer,
        *,
        trace_id: str | None = None,
    ) -> float:
        """Berechnet normalisierte Edit-Distanz [0-1], loggt zu Langfuse.

        Scores werden an die Draft-Generation-Trace gehängt (``trace_id``); ohne
        sie fällt es auf ``correlation_id`` zurück (Altverhalten).
        """
        target = trace_id or correlation_id
        ratio = difflib.SequenceMatcher(None, draft_body, approved_body).ratio()
        distance = 1.0 - ratio
        tracer.log_score(
            trace_id=target,
            name="draft_edit_distance",
            value=distance,
        )
        tracer.log_score(
            trace_id=target,
            name="human_review",
            value=1.0,
            comment="approved",
        )
        if (
            self._alerts is not None
            and distance > self._alerts.thresholds.max_draft_edit_distance
        ):
            self._alerts.check_draft_quality(correlation_id, distance)
        return distance

    def record_rejection(
        self,
        correlation_id: str,
        tracer: LangfuseTracer,
        *,
        trace_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Loggt eine abgelehnte Antwort als ``human_review``-Score 0.0."""
        tracer.log_score(
            trace_id=trace_id or correlation_id,
            name="human_review",
            value=0.0,
            comment=reason or "rejected",
        )

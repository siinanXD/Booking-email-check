"""Edit-Distanz zwischen Draft und freigegebener Antwort."""

from __future__ import annotations

import difflib

from backend.infrastructure.observability.langfuse_client import LangfuseTracer


class ReviewFeedbackTracker:
    """Misst menschliche Korrekturen am Antwortentwurf."""

    def record(
        self,
        correlation_id: str,
        draft_body: str,
        approved_body: str,
        tracer: LangfuseTracer,
    ) -> float:
        """Berechnet normalisierte Edit-Distanz [0-1], loggt zu Langfuse."""
        ratio = difflib.SequenceMatcher(None, draft_body, approved_body).ratio()
        distance = 1.0 - ratio
        tracer.log_score(
            trace_id=correlation_id,
            name="draft_edit_distance",
            value=distance,
        )
        return distance

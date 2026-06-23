"""Tests für Edit-Distanz-Tracking nach Review."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.infrastructure.observability.alerts import AlertService, AlertThresholds
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker


class _MockTracer(LangfuseTracer):
    def __init__(self) -> None:
        super().__init__(enabled=True)
        self._client = MagicMock()
        self.scores: list[tuple[str, str, float]] = []

    def log_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        self.scores.append((trace_id, name, value))


def _scores_named(tracer: _MockTracer, name: str) -> list[tuple[str, str, float]]:
    return [s for s in tracer.scores if s[1] == name]


def test_identical_text_zero_distance() -> None:
    """Identischer Text ergibt Edit-Distanz 0.0."""
    tracer = _MockTracer()
    text = "Sehr geehrte/r Gast, Ihre Anfrage wurde bearbeitet."
    distance = ReviewFeedbackTracker().record("corr-1", text, text, tracer)
    assert distance == 0.0
    assert tracer.scores[0][1] == "draft_edit_distance"


def test_completely_different_text_near_one() -> None:
    """Komplett anderer Text ergibt Distanz nahe 1.0."""
    tracer = _MockTracer()
    distance = ReviewFeedbackTracker().record(
        "corr-2",
        "Sehr geehrte/r Gast, Ihre Anfrage wurde bearbeitet.",
        "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do",
        tracer,
    )
    assert distance >= 0.8


def test_typical_small_correction_moderate_distance() -> None:
    """Typische kleine Korrekturen liegen zwischen 0.1 und 0.4."""
    tracer = _MockTracer()
    draft = "Sehr geehrte/r Gast, Ihre Anfrage wurde bearbeitet."
    approved = "Sehr geehrter Gast, Ihre Anfrage wurde bearbeitet. Viele Grüße"
    distance = ReviewFeedbackTracker().record("corr-3", draft, approved, tracer)
    assert 0.1 <= distance <= 0.4


def test_high_edit_distance_triggers_alert(caplog) -> None:
    """Verify alert when edit distance exceeds configured threshold."""
    tracer = _MockTracer()
    alerts = AlertService(thresholds=AlertThresholds(max_draft_edit_distance=0.4))
    distance = ReviewFeedbackTracker(alerts=alerts).record(
        "corr-4",
        "Sehr geehrte/r Gast, Ihre Anfrage wurde bearbeitet.",
        "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do",
        tracer,
    )
    assert distance > 0.4
    assert any("draft_quality_low" in r.message for r in caplog.records)


def test_approval_logs_human_review_score_on_trace_id() -> None:
    """Freigabe loggt human_review=1.0 an die Draft-Trace, nicht correlation_id."""
    tracer = _MockTracer()
    text = "Sehr geehrter Gast, danke für Ihre Nachricht."
    ReviewFeedbackTracker().record("corr-5", text, text, tracer, trace_id="trace-abc")
    review = _scores_named(tracer, "human_review")
    assert review == [("trace-abc", "human_review", 1.0)]
    # Edit-Distanz hängt ebenfalls an der echten Trace-ID
    assert _scores_named(tracer, "draft_edit_distance")[0][0] == "trace-abc"


def test_rejection_logs_human_review_zero() -> None:
    """Ablehnung loggt human_review=0.0 (ohne Edit-Distanz)."""
    tracer = _MockTracer()
    ReviewFeedbackTracker().record_rejection(
        "corr-6", tracer, trace_id="trace-xyz", reason="Ton unpassend"
    )
    assert _scores_named(tracer, "human_review") == [("trace-xyz", "human_review", 0.0)]
    assert _scores_named(tracer, "draft_edit_distance") == []


def test_record_falls_back_to_correlation_id_without_trace() -> None:
    """Ohne trace_id bleibt das Altverhalten (correlation_id als Ziel)."""
    tracer = _MockTracer()
    text = "Hallo, alles klar."
    ReviewFeedbackTracker().record("corr-7", text, text, tracer)
    assert all(s[0] == "corr-7" for s in tracer.scores)

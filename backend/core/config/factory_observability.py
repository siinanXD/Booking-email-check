"""Observability-Verdrahtung für build_app_context."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.langfuse_setup import (
    configure_langfuse_env,
    tracing_enabled,
)
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker


def build_observability_stack(
    cfg: Settings,
) -> tuple[AlertService, bool, LangfuseTracer, ReviewFeedbackTracker]:
    """Alerts, Tracing-Flag, Langfuse und Review-Feedback."""
    alerts = AlertService(webhook_url=cfg.webhook_alert_url)
    tracing = configure_langfuse_env(cfg) and tracing_enabled(cfg)
    langfuse_tracer = LangfuseTracer(
        enabled=tracing,
        public_key=cfg.langfuse_public_key or None,
        secret_key=cfg.langfuse_secret_key or None,
        host=cfg.langfuse_host,
    )
    feedback_tracker = ReviewFeedbackTracker(alerts=alerts)
    return alerts, tracing, langfuse_tracer, feedback_tracker

"""Legacy-Wrapper – bevorzugt langfuse_setup + @observe (siehe docs/LANGFUSE.md)."""

from __future__ import annotations

from langfuse.decorators import langfuse_context

from backend.infrastructure.observability.langfuse_setup import (
    configure_langfuse_env,
    tracing_enabled,
)

__all__ = ["configure_langfuse_env", "log_mail_cost", "tracing_enabled"]


def log_mail_cost(correlation_id: str, usage: dict[str, float | int]) -> None:
    """Schreibt aggregierte Mail-Kosten auf den aktiven @observe-Trace.

    Keine feste Trace-ID = correlation_id: @observe erzeugt bereits einen Trace
    pro Workflow-Span; ein zweiter Trace mit derselben ID würde kollidieren.
    Stattdessen Metadaten + session_id auf den laufenden Trace legen.
    """
    langfuse_context.update_current_trace(
        session_id=correlation_id,
        metadata={"mail_cost": usage},
    )

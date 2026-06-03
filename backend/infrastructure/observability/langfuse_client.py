"""Legacy-Wrapper – bevorzugt langfuse_setup + @observe (siehe docs/LANGFUSE.md)."""

from __future__ import annotations

from langfuse import Langfuse
from langfuse.decorators import langfuse_context

from backend.infrastructure.observability.langfuse_setup import (
    configure_langfuse_env,
    tracing_enabled,
)

__all__ = [
    "LangfuseTracer",
    "configure_langfuse_env",
    "log_mail_cost",
    "tracing_enabled",
]


class LangfuseTracer:
    """Langfuse-Client für Scores und andere Trace-Ergänzungen."""

    def __init__(
        self,
        enabled: bool,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        self._enabled = enabled
        self._client: Langfuse | None = None
        if enabled and public_key and secret_key:
            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host or "https://cloud.langfuse.com",
            )

    def log_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """Schreibt einen numerischen Score auf einen bestehenden Trace."""
        if not self._enabled or self._client is None:
            return
        self._client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )


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

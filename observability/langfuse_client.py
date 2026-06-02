"""Langfuse-Tracing (optional wenn Keys gesetzt)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from utils.pii import mask_pii


class LangfuseTracer:
    """Dünner Wrapper; no-op wenn Langfuse nicht konfiguriert."""

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str = "https://cloud.langfuse.com",
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled and bool(public_key and secret_key)
        self._client: Any = None
        if self._enabled:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )

    @contextmanager
    def trace(
        self,
        name: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """Span-Kontext; yield trace_id."""
        trace_id = str(uuid4())
        if not self._enabled or self._client is None:
            yield trace_id
            return
        safe_meta = {
            k: mask_pii(str(v)) if isinstance(v, str) else v
            for k, v in (metadata or {}).items()
        }
        trace = self._client.trace(
            id=trace_id,
            name=name,
            session_id=correlation_id,
            metadata=safe_meta,
        )
        try:
            yield trace_id
        finally:
            trace.update(metadata=safe_meta)

    def log_generation(
        self,
        trace_id: str,
        name: str,
        model: str,
        input_text: str,
        output_text: str,
        usage: dict[str, int] | None = None,
    ) -> None:
        """LLM-Generation an Langfuse melden."""
        if not self._enabled or self._client is None:
            return
        self._client.generation(
            trace_id=trace_id,
            name=name,
            model=model,
            input=mask_pii(input_text),
            output=mask_pii(output_text),
            usage=usage,
        )

    def log_mail_cost(
        self,
        correlation_id: str,
        usage: dict[str, float | int],
    ) -> None:
        """Schreibt aggregierte Kosten pro Mail (Session = correlation_id)."""
        if not self._enabled or self._client is None:
            return
        trace = self._client.trace(
            id=correlation_id,
            name="mail_processed",
            session_id=correlation_id,
        )
        trace.update(metadata={"mail_cost": usage})

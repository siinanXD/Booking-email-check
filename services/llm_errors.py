"""Gemeinsame Exception-Typen für LLM- und Tracer-Aufrufe."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from observability.alerts import AlertService

_BASE: list[type[BaseException]] = [
    json.JSONDecodeError,
    ValueError,
    OSError,
    ConnectionError,
    TimeoutError,
]

try:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        RateLimitError,
    )

    _BASE.extend(
        [
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            RateLimitError,
        ]
    )
except ImportError:
    pass

LLM_PIPELINE_ERRORS: tuple[type[BaseException], ...] = tuple(_BASE)


def notify_llm_failure(
    alerts: AlertService | None,
    correlation_id: str,
    step: str,
    exc: BaseException,
) -> None:
    """Meldet Ausfälle bei Klassifikation, Extraktion oder Entwurf."""
    if alerts is None:
        return
    alerts.check_extraction_failure(
        correlation_id,
        f"{step}: {type(exc).__name__}: {exc}",
    )

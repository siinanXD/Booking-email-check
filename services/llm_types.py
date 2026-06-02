"""Gemeinsame LLM-Antworttypen."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMCompletion:
    """Text + Token-Usage für Tracing und Kosten-Alerts."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

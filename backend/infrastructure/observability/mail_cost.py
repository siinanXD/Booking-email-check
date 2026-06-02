"""Aggregierte Token-Kosten pro verarbeiteter Mail."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.ai.services.llm_types import LLMCompletion
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import log_mail_cost

if TYPE_CHECKING:
    from backend.infrastructure.repositories.mail_metrics_repository import (
        MailMetricsRepository,
    )


class MailCostTracker:
    """Sammelt LLM-Token pro correlation_id; finalize meldet Gesamtkosten."""

    def __init__(
        self,
        cost_per_1k_tokens_usd: float = 0.002,
        alerts: AlertService | None = None,
        metrics_repo: MailMetricsRepository | None = None,
        *,
        tracing: bool = False,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._cost_per_1k = cost_per_1k_tokens_usd
        self._alerts = alerts
        self._metrics_repo = metrics_repo
        self._tracing = tracing
        self._prompt_tokens: dict[str, int] = {}
        self._completion_tokens: dict[str, int] = {}

    def add(self, correlation_id: str, completion: LLMCompletion) -> None:
        """Erfasst Token eines LLM-Aufrufs für diese Mail."""
        self._prompt_tokens[correlation_id] = (
            self._prompt_tokens.get(correlation_id, 0) + completion.prompt_tokens
        )
        self._completion_tokens[correlation_id] = (
            self._completion_tokens.get(correlation_id, 0)
            + completion.completion_tokens
        )

    def total_tokens(self, correlation_id: str) -> int:
        """Summe Prompt- und Completion-Tokens für eine Mail."""
        return self._prompt_tokens.get(correlation_id, 0) + self._completion_tokens.get(
            correlation_id, 0
        )

    def cost_usd(self, correlation_id: str) -> float:
        """Geschätzte Kosten in USD für eine Mail."""
        return (self.total_tokens(correlation_id) / 1000.0) * self._cost_per_1k

    def finalize(self, correlation_id: str, *, account_id: str | None = None) -> float:
        """Meldet Gesamtkosten (Alert + Langfuse-Trace-Metadaten); leert den Akku."""
        cost = self.cost_usd(correlation_id)
        usage = {
            "prompt_tokens": self._prompt_tokens.get(correlation_id, 0),
            "completion_tokens": self._completion_tokens.get(correlation_id, 0),
            "total_tokens": self.total_tokens(correlation_id),
            "cost_usd": cost,
        }
        if self._tracing and usage["total_tokens"] > 0:
            log_mail_cost(correlation_id, usage)
        if self._alerts is not None and usage["total_tokens"] > 0:
            self._alerts.check_cost_per_mail(cost, correlation_id)
        if self._metrics_repo is not None and usage["total_tokens"] > 0:
            from backend.infrastructure.repositories.mail_metrics_repository import (
                MailMetricsRepository,
            )

            if isinstance(self._metrics_repo, MailMetricsRepository):
                self._metrics_repo.record(
                    correlation_id,
                    cost_usd=cost,
                    prompt_tokens=int(usage["prompt_tokens"]),
                    completion_tokens=int(usage["completion_tokens"]),
                    account_id=account_id,
                )
        self._prompt_tokens.pop(correlation_id, None)
        self._completion_tokens.pop(correlation_id, None)
        return cost

"""LLM-Gate für unbekannte Absender-Domains (billig, vor classify/extract)."""

from __future__ import annotations

from typing import cast

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.triage import TriageOutcome, TriageResult
from backend.ai.services.classification import LLMClient
from backend.ai.services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from backend.ai.services.prompt_loader import format_resolved_prompt
from backend.core.models.email import IncomingEmail
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import log_token_usage
from backend.infrastructure.observability.mail_cost import MailCostTracker


class TriageLlmService:
    """Klassifiziert UNKNOWN_DOMAIN-Kandidaten per kleinem Modell."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        *,
        max_body_chars: int = 2000,
        tracing: bool = False,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
    ) -> None:
        self._llm = llm
        self._model = model
        self._max_body_chars = max_body_chars
        self._tracing = tracing
        self._alerts = alerts
        self._mail_cost = mail_cost

    def triage_unknown_domain(self, email: IncomingEmail) -> TriageResult:
        """Mappt Mail auf RELEVANT oder SPAM_PHISHING."""
        return cast(TriageResult, self._triage_observed(email))

    @observe(
        name="triage_llm",
        as_type="generation",
        capture_input=False,
        capture_output=False,
    )  # type: ignore[misc]
    def _triage_observed(self, email: IncomingEmail) -> TriageResult:
        if self._tracing:
            langfuse_context.update_current_observation(model=self._model)
        body = (email.body_text or "")[: self._max_body_chars]
        prompt = format_resolved_prompt(
            "booking/triage.md",
            None,
            subject=email.subject or "",
            from_address=email.from_address or "",
            body=body,
        )
        try:
            completion = self._llm.complete(prompt, self._model, temperature=0.0)
            if self._mail_cost is not None:
                self._mail_cost.add(email.correlation_id, completion)
            if self._tracing:
                log_token_usage(completion.prompt_tokens, completion.completion_tokens)
            slug = completion.text.strip().lower().replace(" ", "_")
            if slug == "relevant":
                return TriageResult(
                    outcome=TriageOutcome.RELEVANT,
                    reason="unknown_domain_llm_relevant",
                )
            return TriageResult(
                outcome=TriageOutcome.SPAM_PHISHING,
                reason="unknown_domain_llm_spam",
            )
        except LLM_PIPELINE_ERRORS as exc:
            notify_llm_failure(
                self._alerts,
                email.correlation_id,
                "triage_llm",
                exc,
            )
            return TriageResult(
                outcome=TriageOutcome.SPAM_PHISHING,
                reason="unknown_domain_llm_error",
            )

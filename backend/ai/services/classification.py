"""Klassifikation via OpenAI SDK."""

from __future__ import annotations

from typing import Protocol, cast

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from backend.ai.services.llm_types import LLMCompletion
from backend.ai.services.prompt_loader import format_resolved_prompt_with_few_shots
from backend.core.models.email import StoredEmail
from backend.core.utils.pii import mask_pii
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import log_token_usage
from backend.infrastructure.observability.mail_cost import MailCostTracker
from backend.infrastructure.repositories.platform_llm_config_repository import (
    PlatformLlmConfigRepository,
)
from backend.infrastructure.repositories.tenant_learned_examples_repository import (
    TenantLearnedExamplesRepository,
)


class LLMClient(Protocol):
    """Abstraktion für Tests."""

    def complete(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float | None = None,
    ) -> LLMCompletion:
        """Return a completion for the supplied prompt and model."""
        ...


class ClassificationService:
    """Ordnet BookingIntent zu."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        *,
        tracing: bool = False,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
        llm_config_repo: PlatformLlmConfigRepository | None = None,
        learned_examples_repo: TenantLearnedExamplesRepository | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._llm = llm
        self._model = model
        self._tracing = tracing
        self._alerts = alerts
        self._mail_cost = mail_cost
        self._llm_config_repo = llm_config_repo
        self._learned_examples_repo = learned_examples_repo

    def classify(self, email: StoredEmail) -> BookingIntent:
        """Klassifiziert eine gespeicherte Mail."""
        return cast(BookingIntent, self._classify_observed(email))

    @observe(
        name="classify",
        as_type="generation",
        capture_input=False,
        capture_output=False,
    )  # type: ignore[misc]
    def _classify_observed(self, email: StoredEmail) -> BookingIntent:
        if self._tracing:
            langfuse_context.update_current_trace(
                session_id=email.correlation_id,
                metadata={
                    "message_id": mask_pii(email.message_id),
                    "platform": email.platform,
                    "step": "classify",
                },
            )
            langfuse_context.update_current_observation(model=self._model)
        config = (
            self._llm_config_repo.get_or_default()
            if self._llm_config_repo is not None
            else None
        )
        extra_examples: list[dict[str, object]] = []
        if self._learned_examples_repo is not None and email.account_id:
            extra_examples = self._learned_examples_repo.list_recent(
                email.account_id,
                limit=5,
            )
        prompt = format_resolved_prompt_with_few_shots(
            "booking/classify.md",
            "booking/examples/classify_examples.json",
            config.classify_prompt_override if config else None,
            extra_examples=extra_examples or None,
            subject=email.subject,
            from_address=email.from_address,
            body=email.body_text,
        )
        try:
            temperature = config.classify_temperature if config else None
            completion = self._llm.complete(
                prompt,
                self._model,
                temperature=temperature,
            )
            self._record_cost(email.correlation_id, completion)
            if self._tracing:
                log_token_usage(completion.prompt_tokens, completion.completion_tokens)
            slug = completion.text.strip().lower().replace(" ", "_")
            try:
                intent = BookingIntent(slug)
            except ValueError:
                intent = BookingIntent.OTHER
            if self._tracing:
                langfuse_context.update_current_trace(tags=[intent.value])
            return intent
        except LLM_PIPELINE_ERRORS as exc:
            notify_llm_failure(
                self._alerts,
                email.correlation_id,
                "classify",
                exc,
            )
            return BookingIntent.OTHER

    def _record_cost(self, correlation_id: str, completion: LLMCompletion) -> None:
        if self._mail_cost is not None:
            self._mail_cost.add(correlation_id, completion)

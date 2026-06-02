"""Klassifikation via OpenAI SDK."""

from __future__ import annotations

from typing import Protocol

from models.email import StoredEmail
from observability.alerts import AlertService
from observability.langfuse_client import LangfuseTracer
from observability.mail_cost import MailCostTracker
from schemas.booking.taxonomy import BookingIntent
from services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from services.llm_types import LLMCompletion
from services.prompt_loader import format_prompt_with_few_shots


class LLMClient(Protocol):
    """Abstraktion für Tests."""

    def complete(self, prompt: str, model: str) -> LLMCompletion: ...


class OpenAIClient:
    """OpenAI Chat Completions."""

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def complete(self, prompt: str, model: str) -> LLMCompletion:
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return LLMCompletion(
            text=content.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


class ClassificationService:
    """Ordnet BookingIntent zu."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        tracer: LangfuseTracer | None = None,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
    ) -> None:
        self._llm = llm
        self._model = model
        self._tracer = tracer or LangfuseTracer(enabled=False)
        self._alerts = alerts
        self._mail_cost = mail_cost

    def classify(self, email: StoredEmail) -> BookingIntent:
        """Klassifiziert eine gespeicherte Mail."""
        prompt = format_prompt_with_few_shots(
            "booking/classify.md",
            "booking/examples/classify_examples.json",
            subject=email.subject,
            from_address=email.from_address,
            body=email.body_text,
        )
        try:
            with self._tracer.trace("classify", email.correlation_id) as trace_id:
                completion = self._llm.complete(prompt, self._model)
                self._tracer.log_generation(
                    trace_id,
                    "classify",
                    self._model,
                    prompt,
                    completion.text,
                    usage={
                        "prompt_tokens": completion.prompt_tokens,
                        "completion_tokens": completion.completion_tokens,
                    },
                )
                self._record_cost(email.correlation_id, completion)
            slug = completion.text.strip().lower().replace(" ", "_")
            try:
                return BookingIntent(slug)
            except ValueError:
                return BookingIntent.OTHER
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

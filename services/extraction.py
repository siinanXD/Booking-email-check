"""Extraktion strukturierter Felder via OpenAI SDK."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from models.email import StoredEmail
from observability.alerts import AlertService
from observability.langfuse_client import LangfuseTracer
from observability.mail_cost import MailCostTracker
from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent
from services.classification import LLMClient
from services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from services.prompt_loader import format_prompt_with_few_shots


class ExtractionService:
    """Extrahiert BookingExtraction aus Mail-Text."""

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

    def extract(
        self,
        email: StoredEmail,
        intent: BookingIntent | None = None,
    ) -> BookingExtraction:
        """Extrahiert Felder; setzt intent falls übergeben."""
        prompt = format_prompt_with_few_shots(
            "booking/extract.md",
            "booking/examples/extract_examples.json",
            few_shot_style="extract",
            subject=email.subject,
            body=email.body_text,
        )
        data: dict[str, Any]
        try:
            with self._tracer.trace("extract", email.correlation_id) as trace_id:
                completion = self._llm.complete(prompt, self._model)
                self._tracer.log_generation(
                    trace_id,
                    "extract",
                    self._model,
                    prompt,
                    completion.text,
                    usage={
                        "prompt_tokens": completion.prompt_tokens,
                        "completion_tokens": completion.completion_tokens,
                    },
                )
                if self._mail_cost is not None:
                    self._mail_cost.add(email.correlation_id, completion)
            data = self._parse_json(completion.text)
        except LLM_PIPELINE_ERRORS as exc:
            notify_llm_failure(
                self._alerts,
                email.correlation_id,
                "extract",
                exc,
            )
            data = {"confidence": 0.0}
        if intent is not None:
            data["intent"] = intent
        return BookingExtraction.model_validate(data)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        """Versucht JSON aus der LLM-Antwort zu parsen."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
        payload: dict[str, Any] = json.loads(text)
        for key in ("check_in", "check_out"):
            if key in payload and isinstance(payload[key], str):
                payload[key] = date.fromisoformat(payload[key])
        if "timestamp" in payload and isinstance(payload["timestamp"], str):
            payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
        if "intent" in payload and isinstance(payload["intent"], str):
            try:
                payload["intent"] = BookingIntent(payload["intent"])
            except ValueError:
                payload["intent"] = BookingIntent.OTHER
        payload.setdefault("confidence", 0.8)
        return payload

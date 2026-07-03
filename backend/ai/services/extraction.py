"""Extraktion strukturierter Felder via OpenAI SDK."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, cast

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.services.classification import LLMClient
from backend.ai.services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from backend.ai.services.prompt_loader import format_resolved_prompt_with_few_shots
from backend.core.models.email import StoredEmail
from backend.core.utils.pii import mask_pii
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import log_token_usage
from backend.infrastructure.observability.mail_cost import MailCostTracker
from backend.infrastructure.repositories.platform_llm_config_repository import (
    PlatformLlmConfigRepository,
)

_MAX_KNOWN_PROPERTIES = 50


def _known_properties_hint(names: list[str] | None) -> str:
    """Rendert die Katalog-Namen als Prompt-Block (leer, wenn keiner)."""
    cleaned = [n.strip() for n in names or [] if n and n.strip()]
    if not cleaned:
        return ""
    listed = "\n".join(f"- {name}" for name in cleaned[:_MAX_KNOWN_PROPERTIES])
    return (
        "\nBekannte Unterkünfte dieses Kontos — wenn die Mail eindeutig eine davon "
        "meint, gib property_name EXAKT in dieser Schreibweise zurück; sonst den in "
        "der Mail genannten Namen:\n"
        f"{listed}\n"
    )


class ExtractionService:
    """Extrahiert BookingExtraction aus Mail-Text."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        *,
        tracing: bool = False,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
        llm_config_repo: PlatformLlmConfigRepository | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._llm = llm
        self._model = model
        self._tracing = tracing
        self._alerts = alerts
        self._mail_cost = mail_cost
        self._llm_config_repo = llm_config_repo

    def extract(
        self,
        email: StoredEmail,
        intent: BookingIntent | None = None,
        *,
        known_property_names: list[str] | None = None,
    ) -> BookingExtraction:
        """Extrahiert Felder; setzt intent falls übergeben."""
        return cast(
            BookingExtraction,
            self._extract_observed(email, intent, known_property_names),
        )

    @observe(
        name="extract",
        as_type="generation",
        capture_input=False,
        capture_output=False,
    )  # type: ignore[misc]
    def _extract_observed(
        self,
        email: StoredEmail,
        intent: BookingIntent | None,
        known_property_names: list[str] | None = None,
    ) -> BookingExtraction:
        if self._tracing:
            langfuse_context.update_current_trace(
                session_id=email.correlation_id,
                metadata={
                    "message_id": mask_pii(email.message_id),
                    "step": "extract",
                    "intent": intent.value if intent else None,
                },
            )
            langfuse_context.update_current_observation(model=self._model)
        config = (
            self._llm_config_repo.get_or_default()
            if self._llm_config_repo is not None
            else None
        )
        prompt = format_resolved_prompt_with_few_shots(
            "booking/extract.md",
            "booking/examples/extract_examples.json",
            config.extract_prompt_override if config else None,
            few_shot_style="extract",
            subject=email.subject,
            body=email.body_text,
            known_properties=_known_properties_hint(known_property_names),
        )
        data: dict[str, Any]
        try:
            temperature = config.extract_temperature if config else None
            completion = self._llm.complete(
                prompt,
                self._model,
                temperature=temperature,
            )
            if self._mail_cost is not None:
                self._mail_cost.add(email.correlation_id, completion)
            if self._tracing:
                log_token_usage(completion.prompt_tokens, completion.completion_tokens)
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
        if "price" in payload and isinstance(payload["price"], str):
            price_raw = str(payload["price"]).strip().replace(",", ".")
            match = re.search(r"[\d.]+", price_raw)
            if match:
                try:
                    payload["price"] = float(match.group())
                except ValueError:
                    payload.pop("price", None)
            else:
                payload.pop("price", None)
        payload.setdefault("confidence", 0.8)
        return payload

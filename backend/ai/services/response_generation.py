"""Antwortentwurf mit Grounding."""

from __future__ import annotations

import json
from typing import cast

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services.classification import LLMClient
from backend.ai.services.grounding import GroundingService, sanitize_draft_guest_names
from backend.ai.services.llm_errors import LLM_PIPELINE_ERRORS, notify_llm_failure
from backend.ai.services.prompt_loader import format_resolved_prompt
from backend.ai.services.retrieval import RetrievalHits, RetrievalService
from backend.ai.services.review_fallback import fallback_draft_body
from backend.core.models.email import StoredEmail
from backend.core.models.response import GeneratedResponse
from backend.core.utils.pii import mask_pii
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import log_token_usage
from backend.infrastructure.observability.mail_cost import MailCostTracker
from backend.infrastructure.repositories.platform_llm_config_repository import (
    PlatformLlmConfigRepository,
)


class ResponseGenerationService:
    """Erzeugt Antwortentwürfe aus Retrieval-Kontext."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        retrieval: RetrievalService,
        grounding: GroundingService | None = None,
        *,
        tracing: bool = False,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
        llm_config_repo: PlatformLlmConfigRepository | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._llm = llm
        self._model = model
        self._retrieval = retrieval
        self._grounding = grounding or GroundingService()
        self._tracing = tracing
        self._alerts = alerts
        self._mail_cost = mail_cost
        self._llm_config_repo = llm_config_repo

    def generate_draft(
        self,
        email: StoredEmail,
        extraction: BookingExtraction,
        hits: RetrievalHits | None = None,
    ) -> GeneratedResponse:
        """Erstellt Entwurf und prüft Grounding."""
        return cast(
            GeneratedResponse,
            self._generate_draft_observed(email, extraction, hits),
        )

    @observe(
        name="draft_response",
        as_type="generation",
        capture_input=False,
        capture_output=False,
    )  # type: ignore[misc]
    def _generate_draft_observed(
        self,
        email: StoredEmail,
        extraction: BookingExtraction,
        hits: RetrievalHits | None,
    ) -> GeneratedResponse:
        trace_id: str | None = None
        if self._tracing:
            langfuse_context.update_current_trace(
                session_id=email.correlation_id,
                metadata={
                    "message_id": mask_pii(email.message_id),
                    "step": "draft",
                },
            )
            langfuse_context.update_current_observation(model=self._model)
            trace_id = langfuse_context.get_current_trace_id()
        if hits is None:
            hits = self._retrieval.retrieve(email, extraction)
        facts = self._facts_json(hits, extraction)
        prompt = self._build_prompt(email, extraction, facts)
        try:
            config = (
                self._llm_config_repo.get_or_default()
                if self._llm_config_repo is not None
                else None
            )
            temperature = config.draft_temperature if config else None
            completion = self._llm.complete(
                prompt,
                self._model,
                temperature=temperature,
            )
            if self._mail_cost is not None:
                self._mail_cost.add(email.correlation_id, completion)
            if self._tracing:
                log_token_usage(completion.prompt_tokens, completion.completion_tokens)
            draft = GeneratedResponse(
                correlation_id=email.correlation_id,
                body=completion.text,
                model=self._model,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                langfuse_trace_id=trace_id,
            )
        except LLM_PIPELINE_ERRORS as exc:
            notify_llm_failure(
                self._alerts,
                email.correlation_id,
                "draft_response",
                exc,
            )
            draft = GeneratedResponse(
                correlation_id=email.correlation_id,
                body=fallback_draft_body(email, extraction),
                model=self._model,
                grounding_ok=False,
                langfuse_trace_id=trace_id,
            )
            return draft
        if hits.guest and hits.guest.name:
            draft.body = sanitize_draft_guest_names(draft.body, hits.guest.name)
        draft.grounding_ok = self._grounding.check(draft, hits)
        return draft

    def _build_prompt(
        self,
        email: StoredEmail,
        extraction: BookingExtraction,
        facts: str,
    ) -> str:
        config = (
            self._llm_config_repo.get_or_default()
            if self._llm_config_repo is not None
            else None
        )
        return format_resolved_prompt(
            "booking/draft.md",
            config.draft_prompt_override if config else None,
            platform_tone=_platform_tone(extraction.platform),
            facts=facts,
            body=email.body_text,
        )

    def _facts_json(
        self,
        hits: RetrievalHits,
        extraction: BookingExtraction,
    ) -> str:
        payload = {
            "extraction": extraction.model_dump(mode="json"),
            "reservations": [
                r.model_dump(mode="json") for r in (hits.reservations or [])
            ],
            "guest": hits.guest.model_dump(mode="json") if hits.guest else None,
            "aehnliche_faelle_nur_stil": _compact_similar_cases(
                hits.similar_cases or []
            ),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


_MAX_SNIPPET_CHARS = 280
_MAX_SIMILAR = 5


def _compact_similar_cases(
    similar_cases: list[dict[str, object]],
) -> list[dict[str, object]]:
    """similar_cases auf PII-maskierte Stil-Auszüge reduzieren.

    Entfernt interne Metadaten (account_id, correlation_id, score) und maskiert
    E-Mail/Telefon. Die Auszüge dienen im Draft-Prompt ausschließlich als Ton-/
    Stilreferenz — Fakten stammen nur aus extraction/reservations/guest.
    """
    snippets: list[dict[str, object]] = []
    for case in similar_cases[:_MAX_SIMILAR]:
        text = str(case.get("text") or "").strip()
        if not text:
            continue
        snippets.append(
            {
                "intent": case.get("intent"),
                "auszug": mask_pii(text)[:_MAX_SNIPPET_CHARS],
            }
        )
    return snippets


def _platform_tone(platform: str | None) -> str:
    normalized = (platform or "").strip().lower()
    if normalized == "airbnb":
        return "informell (Du, locker, freundlich)"
    if normalized in {"booking.com", "booking"}:
        return "formell (Sie, höflich und professionell)"
    return "neutral (höflich, weder zu locker noch zu steif)"

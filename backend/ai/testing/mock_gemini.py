"""Gemini-Mock für LLM_MODE=mock (Workflow-Sandbox ohne Google-API)."""

from __future__ import annotations

import json

from backend.ai.services.llm_types import LLMCompletion
from backend.core.models.workflow_media import MediaPart


class MockGemini:
    """Deterministische JSON-Antworten für Workflow-Preview/Tests."""

    def complete_text(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float | None = None,
    ) -> LLMCompletion:
        """Return a deterministic text completion for the supplied prompt."""
        _ = model, temperature
        return LLMCompletion(
            text=_mock_json(prompt),
            prompt_tokens=10,
            completion_tokens=20,
        )

    def complete_multimodal(
        self,
        prompt: str,
        model: str,
        parts: list[MediaPart],
        *,
        temperature: float | None = None,
    ) -> LLMCompletion:
        """Return a deterministic multimodal completion for the supplied prompt."""
        _ = model, temperature
        if "WORKFLOW_DESIGN_FROM_EXAMPLE" in prompt:
            return LLMCompletion(
                text=json.dumps(_mock_workflow_suggest_json(), ensure_ascii=False),
                prompt_tokens=80,
                completion_tokens=120,
            )
        payload = {
            "reference_id": "MOCK-IMG-001",
            "summary": "Mock extraction from multimodal preview",
            "attachment_count": len(parts),
            "confidence": 0.95,
        }
        return LLMCompletion(
            text=json.dumps(payload, ensure_ascii=False),
            prompt_tokens=50,
            completion_tokens=30,
        )


def _mock_workflow_suggest_json() -> dict[str, object]:
    return {
        "label": "Tracking-Mail",
        "slug": "tracking_mail",
        "description": (
            "Erkennt Versandbenachrichtigungen und extrahiert Tracking-Daten."
        ),
        "search_hints": "Tracking Sendung Paket Versand",
        "importance": "high",
        "required_fields": ["tracking_number", "carrier"],
        "optional_fields": ["estimated_delivery"],
        "extraction_schema": {
            "type": "object",
            "required": ["tracking_number", "carrier"],
            "properties": {
                "tracking_number": {"type": "string"},
                "carrier": {"type": "string"},
                "estimated_delivery": {"type": "string"},
            },
        },
        "classify_prompt": (
            "Klassifiziere die Mail. Antworte nur: match oder other.\n"
            "Betreff: {subject}\nAbsender: {from_address}\nInhalt:\n{body}"
        ),
        "extract_prompt": (
            "Extrahiere JSON für Tracking-Mail.\nBetreff: {subject}\nInhalt:\n{body}"
        ),
        "multimodal_prompt": "Lies Tracking-Daten auch aus Anhängen.",
        "match_rules": {
            "subject_keywords": ["sendung", "tracking", "paket"],
            "from_domains": ["dhl.de"],
            "body_keywords": ["tracking", "sendungsnummer"],
        },
        "test_emails": [
            {
                "subject": "Ihre Sendung ist unterwegs",
                "body": "Tracking-Nummer: 1Z999AA10123456784\nVersanddienst: DHL",
                "expected_fields": {"tracking_number": "1Z999AA10123456784"},
            }
        ],
        "supports_multimodal": True,
        "llm_provider": "gemini",
    }


def _mock_json(prompt: str) -> str:
    if "AB123" in prompt or "order_id" in prompt.lower():
        return json.dumps(
            {
                "reference_id": "ORD-9912",
                "summary": "Mock order confirmation",
                "order_id": "ORD-9912",
            },
            ensure_ascii=False,
        )
    if "Extrahiere" in prompt or "extract" in prompt.lower():
        return json.dumps(
            {
                "reference_id": "MOCK-001",
                "summary": "Mock structured extraction",
                "confidence": 0.9,
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {"reference_id": "MOCK-001", "summary": "Mock result"},
        ensure_ascii=False,
    )

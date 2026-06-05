"""OCR-basierter Workflow-Vorschlag: Bild → PaddleOCR → OpenAI-Suggest."""

from __future__ import annotations

from backend.ai.services.ocr_service import extract_text_from_parts
from backend.api.schemas.tenant_workflows import (
    TenantWorkflowSuggestRequest,
    TenantWorkflowSuggestResponse,
)
from backend.api.services.tenant_workflow_suggest_fallback import (
    _llm_suggest,
    _mock_suggest,
)
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.core.models.workflow_media import attachments_to_media_parts

_MAX_OCR_CHARS = 3000


def run_ocr_suggest(
    ctx: AppContext,
    settings: Settings,
    body: TenantWorkflowSuggestRequest,
) -> TenantWorkflowSuggestResponse:
    """Extrahiert Text via PaddleOCR aus Bild-Anhängen, dann OpenAI-Vorschlag.

    Fallback wenn Gemini nicht konfiguriert ist aber Bilder hochgeladen wurden.
    """
    parts = attachments_to_media_parts(body.attachments)
    ocr_text = extract_text_from_parts(parts)

    base_desc = (body.description or "").strip()
    if ocr_text.strip():
        truncated = ocr_text[:_MAX_OCR_CHARS]
        combined = (
            f"{base_desc}\n\nExtrahierter OCR-Text aus Bild:\n{truncated}".strip()
        )
    else:
        combined = base_desc

    enriched = body.model_copy(
        update={"description": combined, "attachments": []},
    )

    if settings.llm_mode.strip().lower() == "mock":
        return _mock_suggest(enriched)
    return _llm_suggest(ctx, settings, enriched)

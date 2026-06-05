"""WhatsApp-Vorschau für Review."""

from __future__ import annotations

from pydantic import BaseModel


class WhatsAppPreviewMessage(BaseModel):
    """Eine Template-Nachricht in der Vorschau."""

    recipient_e164: str
    template_name: str
    template_language: str = "de"
    template_params: list[str] = []
    kind: str = ""
    recipient_role: str = "host"
    generated_body: str = ""
    generated_body_de: str = ""


class WhatsAppPreviewResponse(BaseModel):
    """Vorschau vor Freigabe."""

    correlation_id: str
    enabled: bool = False
    messages: list[WhatsAppPreviewMessage] = []
    note: str | None = None

"""Admin-Diagnose (Mail/WhatsApp pro Mandant)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.api.schemas.mail import MailConnectionResponse

WhatsAppTestTemplate = Literal[
    "hello_world",
    "cleaning_task",
    "status_notice",
    "guest_inquiry",
    "support_ticket",
]


class AdminWhatsAppTemplatesUpdate(BaseModel):
    """Meta-Template-Namen für Mandant (Plattform-Admin)."""

    template_language: str | None = None
    template_cleaning_task: str | None = None
    template_status_notice: str | None = None
    template_guest_inquiry: str | None = None
    template_support_ticket: str | None = None


class AdminWhatsAppInfoResponse(BaseModel):
    """WhatsApp-Konfiguration eines Mandanten (ohne Secrets)."""

    whatsapp_enabled: bool = False
    access_token_configured: bool = False
    phone_number_id: str = ""
    test_recipient: str = ""
    template_language: str = "de"
    templates: dict[str, str] = Field(default_factory=dict)


class AdminWhatsAppTestRequest(BaseModel):
    """Testversand für einen Mandanten."""

    recipient_e164: str | None = None
    template: WhatsAppTestTemplate = "hello_world"


class AdminWhatsAppTestResponse(BaseModel):
    """Ergebnis eines Admin-WhatsApp-Tests."""

    success: bool
    template: WhatsAppTestTemplate
    template_name: str | None = None
    provider_message_id: str | None = None
    error: str | None = None


class AdminMailDiagnosticsResponse(BaseModel):
    """Postfach-Status + optional Testergebnis."""

    account_id: str
    connection: MailConnectionResponse

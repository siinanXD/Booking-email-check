"""Support-Ticket API-Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.core.models.support_ticket import (
    SupportTicketStatus,
    SupportTicketUrgency,
    WhatsAppNotifyStatus,
)


class SupportTicketCreateRequest(BaseModel):
    """POST /api/support/tickets."""

    subject: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=1, max_length=4000)
    urgency: SupportTicketUrgency = "normal"


class SupportTicketResponse(BaseModel):
    """Einzelnes Ticket."""

    ticket_id: str
    account_id: str
    created_by_user_id: str
    created_by_email: str
    subject: str | None = None
    message: str
    urgency: SupportTicketUrgency
    status: SupportTicketStatus
    admin_note: str | None = None
    whatsapp_notify_status: WhatsAppNotifyStatus
    created_at: str
    updated_at: str


class SupportTicketListResponse(BaseModel):
    """Liste eigener Tickets."""

    items: list[SupportTicketResponse] = Field(default_factory=list)
    total: int = 0


class AdminSupportTicketResponse(SupportTicketResponse):
    """Admin-Detail inkl. WhatsApp-Fehler."""

    whatsapp_notify_error: str | None = None
    whatsapp_message_id: str | None = None
    account_display_name: str | None = None


class AdminSupportTicketListResponse(BaseModel):
    """Admin-Übersicht."""

    items: list[AdminSupportTicketResponse] = Field(default_factory=list)
    total: int = 0
    open_count: int = 0


class AdminSupportTicketPatchRequest(BaseModel):
    """PATCH Admin-Status."""

    status: SupportTicketStatus | None = None
    admin_note: str | None = None


class PlatformAdminConfigResponse(BaseModel):
    """Globale Admin-Support-Einstellungen."""

    platform_admin_whatsapp_e164: str = ""
    whatsapp_template_support_ticket: str = "platform_support_ticket_de"
    updated_at: str | None = None


class PlatformAdminConfigUpdateRequest(BaseModel):
    """PUT Admin-Support-Konfiguration."""

    platform_admin_whatsapp_e164: str | None = None
    whatsapp_template_support_ticket: str | None = None

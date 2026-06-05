"""Support-Ticket-Modelle (Mandant → Plattform-Admin)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

SupportTicketUrgency = Literal["low", "normal", "high", "critical"]
SupportTicketStatus = Literal["open", "in_progress", "resolved", "closed"]
WhatsAppNotifyStatus = Literal["pending", "sent", "failed", "skipped"]


class SupportTicketUrgencyLabel(StrEnum):
    """Deutsche Labels für WhatsApp-Template."""

    LOW = "Niedrig"
    NORMAL = "Normal"
    HIGH = "Hoch"
    CRITICAL = "Kritisch"


URGENCY_LABELS: dict[str, str] = {
    "low": SupportTicketUrgencyLabel.LOW,
    "normal": SupportTicketUrgencyLabel.NORMAL,
    "high": SupportTicketUrgencyLabel.HIGH,
    "critical": SupportTicketUrgencyLabel.CRITICAL,
}


class SupportTicketRecord(BaseModel):
    """Persistiertes Support-Ticket."""

    ticket_id: str
    account_id: str
    created_by_user_id: str
    created_by_email: str
    subject: str | None = None
    message: str
    urgency: SupportTicketUrgency
    status: SupportTicketStatus = "open"
    admin_note: str | None = None
    whatsapp_notify_status: WhatsAppNotifyStatus = "pending"
    whatsapp_notify_error: str | None = None
    whatsapp_message_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

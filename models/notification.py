"""WhatsApp-/Notification-Outbox-Modelle."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NotificationKind(StrEnum):
    """Fachliche WhatsApp-Event-Typen."""

    BOOKING_CLEANING_TASK = "booking_cleaning_task"
    BOOKING_STATUS_NOTICE = "booking_status_notice"
    BOOKING_GUEST_INQUIRY = "booking_guest_inquiry"


class NotificationStatus(StrEnum):
    """Outbox-Status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class WhatsAppTemplateMessage(BaseModel):
    """Template-Nachricht an einen Empfänger."""

    recipient_e164: str
    template_name: str
    template_language: str = "de"
    template_params: list[str] = Field(default_factory=list)


class WhatsAppSendResult(BaseModel):
    """Ergebnis eines Provider-Versands."""

    success: bool
    provider_message_id: str | None = None
    error: str | None = None
    dry_run: bool = False


class NotificationOutboxRecord(BaseModel):
    """Persistierter Outbox-Eintrag mit Idempotenz-Schlüssel."""

    id: str
    idempotency_key: str
    correlation_id: str
    kind: NotificationKind
    recipient_e164: str
    template_name: str
    template_language: str
    template_params: list[str]
    status: NotificationStatus
    provider: str | None = None
    provider_message_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = None

"""DTOs für das Benachrichtigungs-Panel (Glocke)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    """Ein Eintrag im Glocken-Panel."""

    id: str
    kind: str  # new_booking | whatsapp_sent | review_waiting | escalation
    title: str
    detail: str = ""
    created_at: str
    read: bool = False
    href: str | None = None


class NotificationsResponse(BaseModel):
    """Feed + Anzahl ungelesener Einträge."""

    items: list[NotificationItem] = Field(default_factory=list)
    unread: int = 0

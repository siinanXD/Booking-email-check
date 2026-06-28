"""DTOs für die Admin-System-Status-Ampel."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class StatusDb(BaseModel):
    ok: bool = False


class StatusPolling(BaseModel):
    expected: bool = False
    stale: bool = False
    last_sync_at: str | None = None
    pollable_accounts: int = 0


class StatusWhatsApp(BaseModel):
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    pending: int = 0


class StatusAccounts(BaseModel):
    connected: int = 0
    error: int = 0
    total: int = 0


class StatusIntegrations(BaseModel):
    langfuse_configured: bool = False
    sentry_configured: bool = False


class AdminStatusResponse(BaseModel):
    """System-Status auf einen Blick (Ampel)."""

    db: StatusDb
    polling: StatusPolling
    whatsapp_24h: StatusWhatsApp
    accounts: StatusAccounts
    integrations: StatusIntegrations
    overall: Literal["ok", "degraded", "down"]

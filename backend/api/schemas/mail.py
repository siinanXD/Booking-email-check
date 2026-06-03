"""Mail-Connection-DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImapPresetItem(BaseModel):
    """Anzeige einer IMAP-Voreinstellung."""

    id: str
    label: str
    host: str
    port: int
    use_ssl: bool


class MailConnectionResponse(BaseModel):
    """GET-Antwort – Passwort wird nie zurückgegeben."""

    provider: str
    status: str
    email_address: str
    preset: str | None = None
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password_set: bool = False
    imap_use_ssl: bool = True
    outlook_auth_mode: str = "application"
    outlook_mailbox: str = ""
    outlook_oauth_connected: bool = False
    last_error: str | None = None
    last_sync_at: str | None = None
    onboarding_completed: bool = False
    imap_presets: list[ImapPresetItem] = Field(default_factory=list)


class MailConnectionUpdate(BaseModel):
    """PUT-Body – leeres Passwort = unverändert lassen."""

    provider: str | None = None
    email_address: str | None = None
    preset: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    imap_use_ssl: bool | None = None
    outlook_auth_mode: str | None = None
    outlook_mailbox: str | None = None
    onboarding_completed: bool | None = None


class MailTestResponse(BaseModel):
    """Ergebnis Verbindungstest."""

    success: bool
    message: str
    mailbox_count: int | None = None


class MailSyncResponse(BaseModel):
    """Ergebnis manueller Postfach-Synchronisation."""

    success: bool
    processed: int = 0
    duplicates: int = 0
    error_count: int = 0
    reprocessed: int = 0
    message: str
    last_sync_at: str | None = None
    item_errors: list[str] = Field(default_factory=list)
    reprocess_errors: list[str] = Field(default_factory=list)

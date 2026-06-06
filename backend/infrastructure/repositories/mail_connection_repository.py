"""Persistente Postfach-Verbindung pro Mandant."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db

MailProvider = Literal["outlook", "imap"]
MailConnectionStatus = Literal["disconnected", "connected", "error"]


class MailConnectionRecord(BaseModel):
    """Postfach-Konfiguration eines Accounts."""

    account_id: str
    provider: MailProvider = "imap"
    status: MailConnectionStatus = "disconnected"
    email_address: str = ""
    preset: str | None = None
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_use_ssl: bool = True
    outlook_auth_mode: str = "application"
    outlook_mailbox: str = ""
    outlook_token_cache: str = ""
    last_error: str | None = None
    last_sync_at: datetime | None = None
    onboarding_completed: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MailConnectionRepository:
    """Collection `mail_connections` – ein Dokument pro Account."""

    COLLECTION = "mail_connections"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index(
            [("onboarding_completed", 1)],
            name="idx_mail_conn_onboarding",
        )

    def get(self, account_id: str) -> MailConnectionRecord | None:
        """Lädt die Verbindung eines Accounts."""
        doc = self._col.find_one({"_id": account_id})
        if doc is None:
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["account_id"] = account_id
        return MailConnectionRecord.model_validate(payload)

    def get_or_create(self, account_id: str) -> MailConnectionRecord:
        """Lädt oder legt leere Verbindung an."""
        existing = self.get(account_id)
        if existing is not None:
            return existing
        record = MailConnectionRecord(account_id=account_id)
        self.save(record)
        return record

    def save(self, record: MailConnectionRecord) -> MailConnectionRecord:
        """Speichert Verbindung."""
        record.updated_at = datetime.now(UTC)
        doc = record.model_dump(mode="json")
        doc["_id"] = record.account_id
        self._col.replace_one({"_id": record.account_id}, doc, upsert=True)
        return record

    def update_status(
        self,
        account_id: str,
        status: MailConnectionStatus,
        *,
        last_error: str | None = None,
        last_sync_at: datetime | None = None,
    ) -> MailConnectionRecord | None:
        """Aktualisiert Verbindungsstatus nach Test/Sync."""
        record = self.get(account_id)
        if record is None:
            return None
        record.status = status
        record.last_error = last_error
        if last_sync_at is not None:
            record.last_sync_at = last_sync_at
        return self.save(record)

    def list_all(self) -> list[MailConnectionRecord]:
        """Lädt alle gespeicherten Postfach-Verbindungen."""
        result: list[MailConnectionRecord] = []
        for doc in self._col.find({}):
            account_id = str(doc["_id"])
            payload = {k: v for k, v in doc.items() if k != "_id"}
            payload["account_id"] = account_id
            result.append(MailConnectionRecord.model_validate(payload))
        return result

    @staticmethod
    def is_pollable(record: MailConnectionRecord) -> bool:
        """Prüft, ob die Verbindung für automatisches Polling konfiguriert ist."""
        if not record.onboarding_completed:
            return False
        if record.provider == "imap":
            username = record.imap_username.strip() or record.email_address.strip()
            return bool(
                record.imap_host.strip() and username and record.imap_password.strip()
            )
        if record.provider == "outlook":
            mode = record.outlook_auth_mode.strip().lower()
            if mode == "oauth":
                return bool(record.outlook_token_cache.strip())
            mailbox = record.outlook_mailbox.strip() or record.email_address.strip()
            return bool(mailbox)
        return False

    def list_pollable(self) -> list[MailConnectionRecord]:
        """Mandanten mit abgeschlossenem Onboarding und gültiger Konfiguration."""
        docs = self._col.find({"onboarding_completed": True})
        result: list[MailConnectionRecord] = []
        for doc in docs:
            account_id = str(doc["_id"])
            payload = {k: v for k, v in doc.items() if k != "_id"}
            payload["account_id"] = account_id
            record = MailConnectionRecord.model_validate(payload)
            if self.is_pollable(record):
                result.append(record)
        return result

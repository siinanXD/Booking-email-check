"""Persistente Plattform-Einstellungen (Singleton in MongoDB)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from repositories.mongo import Db


class PlatformSettingsRecord(BaseModel):
    """Vom Benutzer konfigurierbare Einstellungen (überschreiben .env zur Laufzeit)."""

    id: str = "platform"
    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"
    whatsapp_template_language: str = "de"
    whatsapp_template_cleaning_task: str = "booking_cleaning_task_de"
    whatsapp_template_status_notice: str = "booking_status_notice_de"
    whatsapp_template_guest_inquiry: str = "booking_guest_inquiry_de"
    whatsapp_default_recipients: str = ""
    whatsapp_test_recipient: str = ""
    outlook_mailbox: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlatformSettingsRepository:
    """Collection `platform_settings` – ein Dokument mit `_id: platform`."""

    COLLECTION = "platform_settings"
    DOC_ID = "platform"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def get(self) -> PlatformSettingsRecord | None:
        """Lädt Einstellungen oder None wenn noch nie gespeichert."""
        doc = self._col.find_one({"_id": self.DOC_ID})
        if doc is None:
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = self.DOC_ID
        return PlatformSettingsRecord.model_validate(payload)

    def save(self, record: PlatformSettingsRecord) -> PlatformSettingsRecord:
        """Speichert Einstellungen."""
        record.updated_at = datetime.now(UTC)
        doc = record.model_dump(mode="json")
        doc["_id"] = self.DOC_ID
        doc["id"] = self.DOC_ID
        self._col.replace_one({"_id": self.DOC_ID}, doc, upsert=True)
        return record

    def reset(self) -> None:
        """Löscht gespeicherte Plattform-Einstellungen."""
        self._col.delete_one({"_id": self.DOC_ID})

"""Persistente Plattform-Einstellungen pro Mandant."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db

LEGACY_PLATFORM_DOC_ID = "platform"

# Intents, die einzeln für die Auto-Freigabe aktiviert werden können.
AUTO_APPROVE_INTENTS = ("booking", "cancellation", "inquiry", "change")

# Vom Plattform-Admin pro Account schaltbare Zusatz-Features.
FEATURE_CLEANING_SCHEDULE = "cleaning_schedule"
PLATFORM_FEATURES = (FEATURE_CLEANING_SCHEDULE,)


def _default_auto_approve_intents() -> dict[str, bool]:
    return {intent: False for intent in AUTO_APPROVE_INTENTS}


class AutoApproveSettings(BaseModel):
    """Auto-Freigabe ab Konfidenz (pro Mandant)."""

    enabled: bool = False
    # Schwelle in Prozent (90–100), Standard 97 %.
    threshold: int = Field(default=97, ge=90, le=100)
    per_intent: dict[str, bool] = Field(default_factory=_default_auto_approve_intents)

    def allows(self, intent: str | None) -> bool:
        """True, wenn dieser Intent für die Auto-Freigabe aktiviert ist."""
        if not self.enabled or not intent:
            return False
        return bool(self.per_intent.get(intent, False))


class PlatformSettingsRecord(BaseModel):
    """Vom Benutzer konfigurierbare Einstellungen (überschreiben .env zur Laufzeit)."""

    id: str
    auto_approve: AutoApproveSettings = Field(default_factory=AutoApproveSettings)
    # Generische Feature-Schalter (Plattform-Admin pro Account).
    features: dict[str, bool] = Field(default_factory=dict)
    # Putztermin = Check-out + Offset in Tagen (0 = Abreisetag).
    cleaning_checkout_offset_days: int = Field(default=0, ge=0, le=7)
    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"
    whatsapp_template_language: str = "de"
    whatsapp_template_cleaning_task: str = "booking_cleaning_task_de"
    whatsapp_template_status_notice: str = "booking_status_notice_de"
    whatsapp_template_guest_inquiry: str = "booking_guest_inquiry_de"
    whatsapp_template_cleaning_cancelled: str = "booking_cleaning_cancelled_de"
    whatsapp_default_recipients: str = ""
    whatsapp_test_recipient: str = ""
    outlook_mailbox: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def feature_enabled(self, name: str) -> bool:
        """True, wenn das benannte Zusatz-Feature für den Account aktiv ist."""
        return bool(self.features.get(name, False))


class PlatformSettingsRepository:
    """Collection `platform_settings` – ein Dokument pro Account."""

    COLLECTION = "platform_settings"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def get(self, account_id: str) -> PlatformSettingsRecord | None:
        """Lädt Einstellungen für einen Account."""
        doc = self._col.find_one({"_id": account_id})
        if doc is None:
            legacy = self._col.find_one({"_id": LEGACY_PLATFORM_DOC_ID})
            if legacy is not None:
                payload = {k: v for k, v in legacy.items() if k != "_id"}
                payload["id"] = account_id
                return PlatformSettingsRecord.model_validate(payload)
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = account_id
        return PlatformSettingsRecord.model_validate(payload)

    def save(self, record: PlatformSettingsRecord) -> PlatformSettingsRecord:
        """Speichert Einstellungen für einen Account."""
        record.updated_at = datetime.now(UTC)
        doc = record.model_dump(mode="json")
        account_id = record.id
        doc["_id"] = account_id
        doc["id"] = account_id
        doc["account_id"] = account_id
        self._col.replace_one({"_id": account_id}, doc, upsert=True)
        return record

    def find_account_by_phone_number_id(self, phone_number_id: str) -> str | None:
        """Gibt account_id zurück die diese WhatsApp phone_number_id nutzt."""
        doc = self._col.find_one({"whatsapp_phone_number_id": phone_number_id})
        if doc:
            return str(doc.get("_id", "")) or None
        return None

    def reset(self, account_id: str) -> None:
        """Löscht gespeicherte Einstellungen eines Accounts."""
        self._col.delete_one({"_id": account_id})

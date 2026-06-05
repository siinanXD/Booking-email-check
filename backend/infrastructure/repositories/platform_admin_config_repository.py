"""Globale Plattform-Admin-Einstellungen (Support-Alerts)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db

GLOBAL_ADMIN_CONFIG_ID = "global"


class PlatformAdminConfigRecord(BaseModel):
    """Singleton für Admin-WhatsApp und Support-Template."""

    id: str = GLOBAL_ADMIN_CONFIG_ID
    platform_admin_whatsapp_e164: str = ""
    whatsapp_template_support_ticket: str = "platform_support_ticket_de"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by_user_id: str | None = None


class PlatformAdminConfigRepository:
    """Collection `platform_admin_config`."""

    COLLECTION = "platform_admin_config"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def get(self) -> PlatformAdminConfigRecord | None:
        doc = self._col.find_one({"_id": GLOBAL_ADMIN_CONFIG_ID})
        if doc is None:
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = GLOBAL_ADMIN_CONFIG_ID
        return PlatformAdminConfigRecord.model_validate(payload)

    def get_or_default(self) -> PlatformAdminConfigRecord:
        return self.get() or PlatformAdminConfigRecord()

    def save(
        self,
        record: PlatformAdminConfigRecord,
        *,
        updated_by_user_id: str | None = None,
    ) -> PlatformAdminConfigRecord:
        record.updated_at = datetime.now(UTC)
        record.updated_by_user_id = updated_by_user_id
        doc = record.model_dump(mode="json")
        doc["_id"] = GLOBAL_ADMIN_CONFIG_ID
        doc["id"] = GLOBAL_ADMIN_CONFIG_ID
        self._col.replace_one({"_id": GLOBAL_ADMIN_CONFIG_ID}, doc, upsert=True)
        return record

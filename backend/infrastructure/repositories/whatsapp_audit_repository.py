"""Audit-Log für WhatsApp-Bot-Aktionen (mandantenscharf)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class WhatsAppAuditEntry(BaseModel):
    """Ein Eintrag im WhatsApp-Audit-Log."""

    id: str
    account_id: str
    wa_id: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
    created_at: datetime


class WhatsAppAuditRepository:
    """Collection `whatsapp_audit_log` — jede Bot-Aktion nachvollziehbar."""

    COLLECTION = "whatsapp_audit_log"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("created_at", -1)])
        self._col.create_index([("account_id", 1), ("wa_id", 1)])

    def append(
        self,
        *,
        account_id: str,
        wa_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
        confirmed: bool = False,
    ) -> str:
        """Schreibt einen Audit-Eintrag; gibt dessen ID zurück."""
        entry_id = str(uuid.uuid4())
        self._col.insert_one(
            {
                "_id": entry_id,
                "account_id": account_id,
                "wa_id": wa_id,
                "action": action,
                "payload": payload or {},
                "confirmed": confirmed,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return entry_id

    def list_recent(
        self, *, account_id: str, limit: int = 100
    ) -> list[WhatsAppAuditEntry]:
        """Jüngste Einträge eines Mandanten."""
        query = with_account_filter({}, account_id)
        cursor = self._col.find(query).sort("created_at", -1).limit(max(limit, 1))
        entries: list[WhatsAppAuditEntry] = []
        for doc in cursor:
            entries.append(
                WhatsAppAuditEntry(
                    id=str(doc["_id"]),
                    account_id=str(doc.get("account_id", "")),
                    wa_id=str(doc.get("wa_id", "")),
                    action=str(doc.get("action", "")),
                    payload=doc.get("payload") or {},
                    confirmed=bool(doc.get("confirmed", False)),
                    created_at=datetime.fromisoformat(str(doc["created_at"])),
                )
            )
        return entries

"""Audit-Log für Plattform-Admin-Aktionen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db


class AdminAuditLogEntry(BaseModel):
    """Einzelner Audit-Eintrag."""

    id: str
    action: str
    user_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdminAuditLogRepository:
    """Collection `admin_audit_log`."""

    COLLECTION = "admin_audit_log"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def append(
        self,
        action: str,
        *,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AdminAuditLogEntry:
        entry_id = uuid4().hex
        entry = AdminAuditLogEntry(
            id=entry_id,
            action=action,
            user_id=user_id,
            details=details or {},
        )
        doc = entry.model_dump(mode="json")
        doc["_id"] = entry_id
        self._col.insert_one(doc)
        return entry

    def list_recent(self, limit: int = 100) -> list[AdminAuditLogEntry]:
        """Neueste Audit-Einträge (absteigend nach Zeit)."""
        cursor = self._col.find().sort("created_at", -1).limit(limit)
        return [AdminAuditLogEntry.model_validate(doc) for doc in cursor]

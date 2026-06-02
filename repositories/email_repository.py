"""Persistenz eingegangener E-Mails."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from models.email import ProcessingState, StoredEmail
from repositories.mongo import Db


class EmailRepository:
    """CRUD für die Collection `emails`."""

    COLLECTION = "emails"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def upsert_by_message_id(self, email: StoredEmail) -> StoredEmail:
        """Idempotentes Speichern nach Message-ID."""
        now = datetime.now(UTC)
        doc = email.to_mongo()
        doc["updated_at"] = now.isoformat()
        if email.created_at is None:
            doc["created_at"] = now.isoformat()
        self._col.update_one(
            {"_id": email.message_id},
            {"$set": doc},
            upsert=True,
        )
        stored = self.get_by_message_id(email.message_id)
        if stored is None:
            msg = f"Upsert failed for message_id={email.message_id}"
            raise RuntimeError(msg)
        return stored

    def get_by_message_id(self, message_id: str) -> StoredEmail | None:
        """Lädt eine Mail anhand der Message-ID."""
        doc = self._col.find_one({"_id": message_id})
        if doc is None:
            doc = self._col.find_one({"message_id": message_id})
        if doc is None:
            return None
        return StoredEmail.from_mongo(doc)

    def update_processing_state(
        self,
        message_id: str,
        state: ProcessingState,
        **extra: Any,
    ) -> StoredEmail | None:
        """Aktualisiert Verarbeitungsstatus und optionale Felder."""
        update: dict[str, Any] = {
            "processing_state": state.value,
            "updated_at": datetime.now(UTC).isoformat(),
            **extra,
        }
        self._col.update_one({"_id": message_id}, {"$set": update})
        return self.get_by_message_id(message_id)

    def list_by_correlation_id(self, correlation_id: str) -> list[StoredEmail]:
        """Alle Mails einer Correlation-ID."""
        cursor = self._col.find({"correlation_id": correlation_id})
        return [StoredEmail.from_mongo(doc) for doc in cursor]

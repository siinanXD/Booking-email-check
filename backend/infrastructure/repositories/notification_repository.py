"""Outbox/Sendelog für WhatsApp-Benachrichtigungen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from backend.core.models.notification import (
    NotificationKind,
    NotificationOutboxRecord,
    NotificationStatus,
)
from backend.infrastructure.repositories.mongo import Db


class NotificationRepository:
    """Collection `notification_outbox` mit Idempotenz über `idempotency_key`."""

    COLLECTION = "notification_outbox"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index("idempotency_key", unique=True)
        self._col.create_index("correlation_id")

    def list_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[NotificationOutboxRecord]:
        """Alle Benachrichtigungen zu einer Correlation-ID."""
        cursor = self._col.find({"correlation_id": correlation_id}).sort(
            "created_at", 1
        )
        return [NotificationOutboxRecord.model_validate(doc) for doc in cursor]

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> NotificationOutboxRecord | None:
        """Lädt einen Outbox-Eintrag per Idempotenz-Schlüssel."""
        doc = self._col.find_one({"idempotency_key": idempotency_key})
        if doc is None:
            return None
        return NotificationOutboxRecord.model_validate(doc)

    def try_claim(
        self, record: NotificationOutboxRecord
    ) -> NotificationOutboxRecord | None:
        """Legt Outbox-Eintrag an; bei Duplikat `None` (bereits verarbeitet)."""
        existing = self.get_by_idempotency_key(record.idempotency_key)
        if existing is not None:
            return None
        doc = record.model_dump(mode="json")
        doc["_id"] = record.id
        try:
            self._col.insert_one(doc)
        except DuplicateKeyError:
            return None
        return record

    def mark_sent(
        self,
        record_id: str,
        *,
        provider: str,
        provider_message_id: str | None,
    ) -> None:
        """Markiert Eintrag als erfolgreich versendet."""
        now = datetime.now(UTC).isoformat()
        self._col.update_one(
            {"_id": record_id},
            {
                "$set": {
                    "status": NotificationStatus.SENT.value,
                    "provider": provider,
                    "provider_message_id": provider_message_id,
                    "sent_at": now,
                    "error": None,
                }
            },
        )

    def mark_failed(self, record_id: str, error: str) -> None:
        """Markiert Eintrag als fehlgeschlagen."""
        self._col.update_one(
            {"_id": record_id},
            {
                "$set": {
                    "status": NotificationStatus.FAILED.value,
                    "error": error,
                }
            },
        )

    def mark_skipped(self, record_id: str, reason: str) -> None:
        """Markiert Eintrag als übersprungen (z. B. deaktiviert)."""
        self._col.update_one(
            {"_id": record_id},
            {
                "$set": {
                    "status": NotificationStatus.SKIPPED.value,
                    "error": reason,
                }
            },
        )

    def new_record(
        self,
        *,
        idempotency_key: str,
        correlation_id: str,
        kind: NotificationKind,
        recipient_e164: str,
        template_name: str,
        template_language: str,
        template_params: list[str],
        status: NotificationStatus = NotificationStatus.PENDING,
    ) -> NotificationOutboxRecord:
        """Erzeugt einen neuen Outbox-Datensatz (noch nicht persistiert)."""
        record_id = uuid4().hex
        return NotificationOutboxRecord(
            id=record_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            kind=kind,
            recipient_e164=recipient_e164,
            template_name=template_name,
            template_language=template_language,
            template_params=template_params,
            status=status,
        )

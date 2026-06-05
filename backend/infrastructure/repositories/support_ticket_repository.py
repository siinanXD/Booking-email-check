"""Support-Tickets (Mandant → Plattform-Admin)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pymongo.collection import Collection

from backend.core.models.support_ticket import (
    SupportTicketRecord,
    SupportTicketStatus,
    SupportTicketUrgency,
    WhatsAppNotifyStatus,
)
from backend.infrastructure.repositories.mongo import Db


class SupportTicketRepository:
    """Collection `support_tickets`."""

    COLLECTION = "support_tickets"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index("ticket_id", unique=True)
        self._col.create_index([("status", 1), ("urgency", 1), ("created_at", -1)])
        self._col.create_index([("account_id", 1), ("created_at", -1)])

    def create(
        self,
        *,
        account_id: str,
        created_by_user_id: str,
        created_by_email: str,
        message: str,
        urgency: SupportTicketUrgency,
        subject: str | None = None,
    ) -> SupportTicketRecord:
        now = datetime.now(UTC)
        ticket_id = str(uuid4())
        doc = {
            "_id": ticket_id,
            "ticket_id": ticket_id,
            "account_id": account_id,
            "created_by_user_id": created_by_user_id,
            "created_by_email": created_by_email.lower().strip(),
            "subject": (subject or "").strip() or None,
            "message": message.strip(),
            "urgency": urgency,
            "status": "open",
            "admin_note": None,
            "whatsapp_notify_status": "pending",
            "whatsapp_notify_error": None,
            "whatsapp_message_id": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._col.insert_one(doc)
        return self._from_doc(doc)

    def get_by_ticket_id(self, ticket_id: str) -> SupportTicketRecord | None:
        doc = self._col.find_one({"ticket_id": ticket_id})
        if doc is None:
            return None
        return self._from_doc(doc)

    def list_for_account(
        self,
        account_id: str,
        *,
        limit: int = 50,
    ) -> list[SupportTicketRecord]:
        cursor = (
            self._col.find({"account_id": account_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [self._from_doc(doc) for doc in cursor]

    def list_admin(
        self,
        *,
        status: SupportTicketStatus | None = None,
        urgency: SupportTicketUrgency | None = None,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[SupportTicketRecord]:
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status
        if urgency is not None:
            query["urgency"] = urgency
        if account_id:
            query["account_id"] = account_id
        cursor = self._col.find(query).sort("created_at", -1).limit(limit)
        return [self._from_doc(doc) for doc in cursor]

    def count_open_critical(self) -> int:
        return int(
            self._col.count_documents(
                {
                    "status": {"$in": ["open", "in_progress"]},
                    "urgency": "critical",
                }
            )
        )

    def count_open(self) -> int:
        return int(
            self._col.count_documents({"status": {"$in": ["open", "in_progress"]}})
        )

    def update_admin(
        self,
        ticket_id: str,
        *,
        status: SupportTicketStatus | None = None,
        admin_note: str | None = None,
    ) -> SupportTicketRecord | None:
        update: dict[str, Any] = {"updated_at": datetime.now(UTC).isoformat()}
        if status is not None:
            update["status"] = status
        if admin_note is not None:
            update["admin_note"] = admin_note.strip() or None
        self._col.update_one({"ticket_id": ticket_id}, {"$set": update})
        return self.get_by_ticket_id(ticket_id)

    def update_whatsapp_status(
        self,
        ticket_id: str,
        *,
        status: WhatsAppNotifyStatus,
        error: str | None = None,
        message_id: str | None = None,
    ) -> SupportTicketRecord | None:
        update: dict[str, Any] = {
            "whatsapp_notify_status": status,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if error is not None:
            update["whatsapp_notify_error"] = error[:500]
        if message_id is not None:
            update["whatsapp_message_id"] = message_id
        self._col.update_one({"ticket_id": ticket_id}, {"$set": update})
        return self.get_by_ticket_id(ticket_id)

    @staticmethod
    def _from_doc(doc: dict[str, Any]) -> SupportTicketRecord:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "ticket_id" not in payload:
            payload["ticket_id"] = str(doc.get("_id", ""))
        for field in ("created_at", "updated_at"):
            value = payload.get(field)
            if isinstance(value, str):
                payload[field] = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return SupportTicketRecord.model_validate(payload)

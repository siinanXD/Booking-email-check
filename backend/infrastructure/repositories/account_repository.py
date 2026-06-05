"""Mandanten-Accounts (Multi-Tenant)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db

AccountStatus = Literal["pending", "active", "rejected", "suspended"]
AccountType = Literal["private", "business"]


class AccountRecord(BaseModel):
    """Persistierter Mandant."""

    id: str
    display_name: str
    account_type: AccountType = "private"
    company_name: str | None = None
    phone: str | None = None
    contact_email: str
    status: AccountStatus = "pending"
    rejection_reason: str | None = None
    mail_ingest_anchor_at: datetime | None = None
    mail_ingest_lookback_count: int = 50
    mail_initial_sync_completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AccountRepository:
    """Collection `accounts`."""

    COLLECTION = "accounts"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def get_by_id(self, account_id: str) -> AccountRecord | None:
        """Lädt Account per ID."""
        doc = self._col.find_one({"_id": account_id})
        if doc is None:
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = doc["_id"]
        return AccountRecord.model_validate(payload)

    def create(
        self,
        *,
        display_name: str,
        contact_email: str,
        account_type: AccountType = "private",
        company_name: str | None = None,
        phone: str | None = None,
        status: AccountStatus = "pending",
    ) -> AccountRecord:
        """Legt einen Account an."""
        account_id = uuid4().hex
        now = datetime.now(UTC)
        doc = {
            "_id": account_id,
            "id": account_id,
            "display_name": display_name.strip(),
            "account_type": account_type,
            "company_name": (company_name or "").strip() or None,
            "phone": (phone or "").strip() or None,
            "contact_email": contact_email.lower().strip(),
            "status": status,
            "rejection_reason": None,
            "mail_ingest_anchor_at": now.isoformat(),
            "mail_ingest_lookback_count": 50,
            "mail_initial_sync_completed_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._col.insert_one(doc)
        return AccountRecord.model_validate(doc)

    def list_by_status(
        self, status: AccountStatus | None = None
    ) -> list[AccountRecord]:
        """Listet Accounts, optional gefiltert nach Status."""
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status
        docs = self._col.find(query).sort("created_at", -1)
        result: list[AccountRecord] = []
        for doc in docs:
            payload = {k: v for k, v in doc.items() if k != "_id"}
            payload["id"] = doc["_id"]
            result.append(AccountRecord.model_validate(payload))
        return result

    def update_status(
        self,
        account_id: str,
        status: AccountStatus,
        *,
        rejection_reason: str | None = None,
    ) -> AccountRecord | None:
        """Aktualisiert den Account-Status."""
        now = datetime.now(UTC)
        update: dict[str, Any] = {
            "status": status,
            "updated_at": now.isoformat(),
        }
        if rejection_reason is not None:
            update["rejection_reason"] = rejection_reason.strip() or None
        elif status != "rejected":
            update["rejection_reason"] = None
        self._col.update_one({"_id": account_id}, {"$set": update})
        return self.get_by_id(account_id)

    def mark_initial_sync_completed(self, account_id: str) -> None:
        """Setzt Flag nach erstem Initial-Poll."""
        now = datetime.now(UTC)
        self._col.update_one(
            {"_id": account_id, "mail_initial_sync_completed_at": None},
            {
                "$set": {
                    "mail_initial_sync_completed_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )

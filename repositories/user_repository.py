"""Web-Dashboard-Benutzer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from repositories.mongo import Db


class UserRecord(BaseModel):
    """Persistierter Benutzer."""

    id: str
    email: str
    password_hash: str
    role: str = "admin"
    whatsapp_phone_e164: str | None = None
    whatsapp_enabled: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserRepository:
    """Collection `users`."""

    COLLECTION = "users"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def get_by_email(self, email: str) -> UserRecord | None:
        """Lädt Benutzer per E-Mail."""
        doc = self._col.find_one({"email": email.lower()})
        if doc is None:
            return None
        return UserRecord.model_validate(doc)

    def get_by_id(self, user_id: str) -> UserRecord | None:
        """Lädt Benutzer per ID."""
        doc = self._col.find_one({"_id": user_id})
        if doc is None:
            return None
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = doc["_id"]
        return UserRecord.model_validate(payload)

    def create(self, email: str, password_hash: str, role: str = "admin") -> UserRecord:
        """Legt einen Benutzer an."""
        user_id = uuid4().hex
        now = datetime.now(UTC)
        doc = {
            "_id": user_id,
            "id": user_id,
            "email": email.lower(),
            "password_hash": password_hash,
            "role": role,
            "created_at": now.isoformat(),
        }
        self._col.insert_one(doc)
        return UserRecord.model_validate(doc)

    def ensure_admin(self, email: str, password_hash: str) -> UserRecord:
        """Idempotenter Admin-Seed."""
        existing = self.get_by_email(email)
        if existing is not None:
            return existing
        return self.create(email, password_hash, role="admin")

    def list_whatsapp_recipient_phones(self) -> list[str]:
        """E.164-Nummern aktiver WhatsApp-Empfänger (Dashboard-Benutzer)."""
        phones: list[str] = []
        query = {
            "whatsapp_enabled": True,
            "whatsapp_phone_e164": {"$exists": True, "$nin": [None, ""]},
        }
        for doc in self._col.find(query):
            phone = str(doc.get("whatsapp_phone_e164") or "").strip()
            if phone:
                phones.append(phone)
        return phones

    def update_whatsapp_profile(
        self,
        user_id: str,
        *,
        whatsapp_phone_e164: str | None,
        whatsapp_enabled: bool,
    ) -> UserRecord | None:
        """Aktualisiert WhatsApp-Profil des Benutzers."""
        phone = (whatsapp_phone_e164 or "").strip() or None
        self._col.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "whatsapp_phone_e164": phone,
                    "whatsapp_enabled": whatsapp_enabled,
                }
            },
        )
        return self.get_by_id(user_id)

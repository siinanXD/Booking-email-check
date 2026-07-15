"""Web-Dashboard-Benutzer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.core.utils.phone import normalize_phone_digits
from backend.infrastructure.repositories.mongo import Db

UserRole = Literal["owner", "admin", "member", "platform_admin"]


class UserRecord(BaseModel):
    """Persistierter Benutzer."""

    id: str
    email: str
    password_hash: str
    account_id: str | None = None
    role: UserRole = "owner"
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    whatsapp_phone_e164: str | None = None
    whatsapp_enabled: bool = False
    is_locked: bool = False
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
        return self._from_doc(doc)

    def get_by_id(self, user_id: str) -> UserRecord | None:
        """Lädt Benutzer per ID."""
        doc = self._col.find_one({"_id": user_id})
        if doc is None:
            return None
        return self._from_doc(doc)

    def create(
        self,
        email: str,
        password_hash: str,
        *,
        account_id: str | None = None,
        role: UserRole = "owner",
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
    ) -> UserRecord:
        """Legt einen Benutzer an."""
        user_id = uuid4().hex
        now = datetime.now(UTC)
        doc = {
            "_id": user_id,
            "id": user_id,
            "email": email.lower(),
            "password_hash": password_hash,
            "account_id": account_id,
            "role": role,
            "first_name": (first_name or "").strip() or None,
            "last_name": (last_name or "").strip() or None,
            "phone": (phone or "").strip() or None,
            "created_at": now.isoformat(),
        }
        self._col.insert_one(doc)
        return UserRecord.model_validate(doc)

    def ensure_platform_admin(
        self,
        email: str,
        password_hash: str,
        *,
        account_id: str,
    ) -> UserRecord:
        """Idempotenter Plattform-Admin-Seed."""
        existing = self.get_by_email(email)
        if existing is not None:
            return existing
        return self.create(
            email,
            password_hash,
            account_id=account_id,
            role="platform_admin",
        )

    def list_whatsapp_recipient_phones(
        self,
        account_id: str | None = None,
    ) -> list[str]:
        """E.164-Nummern aktiver WhatsApp-Empfänger (Dashboard-Benutzer)."""
        phones: list[str] = []
        query: dict[str, Any] = {
            "whatsapp_enabled": True,
            "whatsapp_phone_e164": {"$exists": True, "$nin": [None, ""]},
        }
        if account_id:
            query["account_id"] = account_id
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

    def set_locked(self, user_id: str, locked: bool) -> UserRecord | None:
        """Sperrt oder entsperrt einen Benutzer."""
        self._col.update_one({"_id": user_id}, {"$set": {"is_locked": locked}})
        return self.get_by_id(user_id)

    def reset_password_hash(self, user_id: str, new_hash: str) -> UserRecord | None:
        """Setzt den Passwort-Hash zurück (Admin-seitig)."""
        self._col.update_one({"_id": user_id}, {"$set": {"password_hash": new_hash}})
        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        """Löscht einen Benutzer. Gibt True zurück wenn gefunden."""
        result = self._col.delete_one({"_id": user_id})
        return result.deleted_count > 0

    def find_account_ids_by_whatsapp(self, digits: str) -> list[str]:
        """Konten mit einem Dashboard-Nutzer, dessen WhatsApp-Nummer passt.

        Plattform-weit (bewusst NICHT tenant-scoped) – für das Routing
        eingehender Nachrichten über eine geteilte Absendernummer. Der
        Vergleich erfolgt ziffern-normalisiert (E.164-Formatierung egal).
        """
        if not digits:
            return []
        found: list[str] = []
        query: dict[str, Any] = {
            "whatsapp_phone_e164": {"$exists": True, "$nin": [None, ""]}
        }
        for doc in self._col.find(query):
            account_id = doc.get("account_id")
            if (
                account_id
                and normalize_phone_digits(str(doc.get("whatsapp_phone_e164") or ""))
                == digits
            ):
                found.append(str(account_id))
        return found

    def list_by_account_id(self, account_id: str) -> list[UserRecord]:
        """Alle Benutzer eines Mandanten."""
        users: list[UserRecord] = []
        for doc in self._col.find({"account_id": account_id}).sort("created_at", 1):
            users.append(self._from_doc(doc))
        return users

    def count_for_account(self, account_id: str) -> int:
        """Anzahl Benutzer eines Mandanten."""
        return int(self._col.count_documents({"account_id": account_id}))

    def count_by_role(self, role: UserRole) -> int:
        """Anzahl der Benutzer mit einer bestimmten Rolle."""
        return self._col.count_documents({"role": role})

    @staticmethod
    def _from_doc(doc: dict[str, Any]) -> UserRecord:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = doc["_id"]
        return UserRecord.model_validate(payload)

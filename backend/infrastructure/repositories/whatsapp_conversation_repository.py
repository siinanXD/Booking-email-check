"""Konversations-State pro WhatsApp-Chat (mandantenscharf, TTL 24h)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo.collection import Collection

from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter

_MAX_PROCESSED_IDS = 50


class WhatsAppConversationRepository:
    """Collection `whatsapp_conversations`.

    Ein Dokument pro (account_id, wa_id): wartende Bestätigung
    (`pending_action`) und zuletzt verarbeitete Meta-Message-IDs
    (Dedupe gegen Webhook-Retries). TTL-Index räumt inaktive Chats
    nach 24h auf.
    """

    COLLECTION = "whatsapp_conversations"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("wa_id", 1)], unique=True)
        self._col.create_index("expires_at", expireAfterSeconds=0)

    @staticmethod
    def _key(account_id: str, wa_id: str) -> dict[str, Any]:
        return {"account_id": account_id, "wa_id": wa_id}

    def get_pending_action(
        self, *, account_id: str, wa_id: str
    ) -> dict[str, Any] | None:
        """Wartende Bestätigung, sofern nicht abgelaufen."""
        query = with_account_filter({"wa_id": wa_id}, account_id)
        doc = self._col.find_one(query)
        if not doc:
            return None
        pending = doc.get("pending_action")
        if not isinstance(pending, dict):
            return None
        expires = pending.get("expires_at")
        if isinstance(expires, str):
            try:
                if datetime.fromisoformat(expires) < datetime.now(UTC):
                    return None
            except ValueError:
                return None
        return pending

    def set_pending_action(
        self,
        *,
        account_id: str,
        wa_id: str,
        action: dict[str, Any] | None,
        ttl_minutes: int = 15,
    ) -> None:
        """Setzt oder löscht die wartende Bestätigung."""
        now = datetime.now(UTC)
        if action is not None:
            action = {
                **action,
                "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
            }
        self._col.update_one(
            self._key(account_id, wa_id),
            {
                "$set": {
                    "pending_action": action,
                    "updated_at": now.isoformat(),
                    "expires_at": now + timedelta(hours=24),
                }
            },
            upsert=True,
        )

    def mark_message_processed(
        self, *, account_id: str, wa_id: str, message_id: str
    ) -> bool:
        """True wenn die Message-ID neu ist; False bei Duplikat (Meta-Retry)."""
        if not message_id:
            return True
        query = with_account_filter({"wa_id": wa_id}, account_id)
        doc = self._col.find_one(query, {"processed_ids": 1})
        processed = doc.get("processed_ids", []) if doc else []
        if message_id in processed:
            return False
        now = datetime.now(UTC)
        self._col.update_one(
            self._key(account_id, wa_id),
            {
                "$push": {
                    "processed_ids": {
                        "$each": [message_id],
                        "$slice": -_MAX_PROCESSED_IDS,
                    }
                },
                "$set": {
                    "updated_at": now.isoformat(),
                    "expires_at": now + timedelta(hours=24),
                },
            },
            upsert=True,
        )
        return True

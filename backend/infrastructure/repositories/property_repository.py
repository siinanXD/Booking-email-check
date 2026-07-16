"""Unterkünfte pro Mandant."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection

from backend.core.models.entities import Property
from backend.infrastructure.repositories.domain_collections import PROPERTIES
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter

# Altbestände haben kein `active`-Feld – `$ne: False` zählt sie als aktiv.
_ACTIVE: dict[str, Any] = {"active": {"$ne": False}}


class PropertyRepository:
    """Collection `properties`."""

    COLLECTION = PROPERTIES

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("name", 1)])

    def upsert(
        self,
        prop: Property,
        *,
        account_id: str | None = None,
    ) -> Property:
        """Unterkunft speichern oder aktualisieren."""
        doc = prop.to_mongo()
        resolved_account = account_id or prop.account_id
        if resolved_account:
            doc["account_id"] = resolved_account
        self._col.update_one(
            {"_id": prop.property_id},
            {"$set": doc},
            upsert=True,
        )
        return prop

    def get_by_id(
        self,
        property_id: str,
        *,
        account_id: str | None = None,
    ) -> Property | None:
        """Lädt eine Unterkunft."""
        query = with_account_filter({"_id": property_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None:
            return None
        return Property.from_mongo(doc)

    def count_for_account(self, account_id: str) -> int:
        """Anzahl aktiver Unterkünfte eines Mandanten (zählt fürs Kontingent)."""
        query = with_account_filter(_ACTIVE, account_id)
        return int(self._col.count_documents(query))

    def list_all(
        self,
        *,
        account_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[Property]:
        """Unterkünfte eines Mandanten; archivierte nur auf Wunsch.

        ``include_inactive=True`` braucht, wer gegen den Gesamtbestand prüft
        (z. B. entity_sync), damit archivierte Objekte nicht aus Buchungs-
        mails neu angelegt werden.
        """
        base: dict[str, Any] = {} if include_inactive else dict(_ACTIVE)
        query = with_account_filter(base, account_id)
        return [Property.from_mongo(doc) for doc in self._col.find(query)]

    def deactivate(
        self,
        property_id: str,
        *,
        account_id: str | None = None,
    ) -> bool:
        """Soft-Delete: archiviert das Objekt (historische Daten bleiben)."""
        query = with_account_filter({"_id": property_id}, account_id)
        result = self._col.update_one(query, {"$set": {"active": False}})
        return result.matched_count > 0

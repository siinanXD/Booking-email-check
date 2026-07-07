"""Unterkünfte pro Mandant."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection

from backend.core.models.entities import Property
from backend.infrastructure.repositories.domain_collections import PROPERTIES
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


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
        """Anzahl Unterkünfte eines Mandanten."""
        query = with_account_filter({}, account_id)
        return int(self._col.count_documents(query))

    def list_all(
        self,
        *,
        account_id: str | None = None,
    ) -> list[Property]:
        """Alle Unterkünfte eines Mandanten."""
        query = with_account_filter({}, account_id)
        return [Property.from_mongo(doc) for doc in self._col.find(query)]

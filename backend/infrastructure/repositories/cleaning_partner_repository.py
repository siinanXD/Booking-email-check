"""CRUD für Putzpartner (mandantenscharf)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from backend.features.cleaning.models import CleaningPartner
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class CleaningPartnerRepository:
    """Collection `cleaning_partners` mit account_id-Scope."""

    COLLECTION = "cleaning_partners"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("active", 1)])
        self._col.create_index([("account_id", 1), ("property_names", 1)])

    def upsert(
        self,
        partner: CleaningPartner,
        *,
        account_id: str | None = None,
    ) -> CleaningPartner:
        """Putzpartner speichern oder aktualisieren."""
        resolved = account_id or partner.account_id
        if resolved:
            partner.account_id = resolved
        partner.updated_at = datetime.now(UTC)
        doc = partner.to_mongo()
        self._col.update_one(
            {"_id": partner.partner_id},
            {"$set": doc},
            upsert=True,
        )
        return partner

    def get(
        self,
        partner_id: str,
        *,
        account_id: str | None = None,
    ) -> CleaningPartner | None:
        """Putzpartner anhand partner_id."""
        query = with_account_filter({"_id": partner_id}, account_id)
        doc = self._col.find_one(query)
        return None if doc is None else CleaningPartner.from_mongo(doc)

    def list_partners(
        self,
        *,
        account_id: str | None = None,
        active_only: bool = False,
    ) -> list[CleaningPartner]:
        """Alle Putzpartner eines Accounts (optional nur aktive)."""
        base: dict[str, Any] = {"active": True} if active_only else {}
        query = with_account_filter(base, account_id)
        cursor = self._col.find(query).sort("name", 1)
        return [CleaningPartner.from_mongo(doc) for doc in cursor]

    def find_for_property(
        self,
        property_name: str | None,
        *,
        account_id: str | None = None,
    ) -> list[CleaningPartner]:
        """Aktive Putzpartner, die einer Wohnung zugeordnet sind."""
        if not property_name or not property_name.strip():
            return []
        base: dict[str, Any] = {
            "active": True,
            "property_names": property_name.strip(),
        }
        query = with_account_filter(base, account_id)
        cursor = self._col.find(query).sort("name", 1)
        return [CleaningPartner.from_mongo(doc) for doc in cursor]

    def deactivate(
        self,
        partner_id: str,
        *,
        account_id: str | None = None,
    ) -> bool:
        """Soft-Delete: deaktiviert den Partner (historische Aufträge bleiben)."""
        query = with_account_filter({"_id": partner_id}, account_id)
        result = self._col.update_one(
            query,
            {"$set": {"active": False, "updated_at": datetime.now(UTC).isoformat()}},
        )
        return result.matched_count > 0

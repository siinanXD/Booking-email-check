"""CRUD für Putzaufträge (mandantenscharf)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pymongo.collection import Collection

from backend.features.cleaning.models import CleaningTask
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class CleaningTaskRepository:
    """Collection `cleaning_tasks` mit account_id-Scope."""

    COLLECTION = "cleaning_tasks"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index([("account_id", 1), ("booking_number", 1)])
        self._col.create_index([("account_id", 1), ("status", 1)])
        self._col.create_index([("account_id", 1), ("cleaning_date", 1)])

    def upsert(
        self,
        task: CleaningTask,
        *,
        account_id: str | None = None,
    ) -> CleaningTask:
        """Putzauftrag speichern oder aktualisieren (idempotent per task_id)."""
        resolved = account_id or task.account_id
        if resolved:
            task.account_id = resolved
        doc = task.to_mongo()
        self._col.update_one(
            {"_id": task.task_id},
            {"$set": doc},
            upsert=True,
        )
        return task

    def get(
        self,
        task_id: str,
        *,
        account_id: str | None = None,
    ) -> CleaningTask | None:
        """Putzauftrag anhand task_id."""
        query = with_account_filter({"_id": task_id}, account_id)
        doc = self._col.find_one(query)
        return None if doc is None else CleaningTask.from_mongo(doc)

    def count_open_tasks(self, *, account_id: str) -> int:
        """Offene Aufträge (unassigned/scheduled/notified) eines Accounts."""
        query = with_account_filter(
            {"status": {"$in": ["unassigned", "scheduled", "notified"]}},
            account_id,
        )
        return int(self._col.count_documents(query))

    def find_by_booking_number(
        self,
        booking_number: str,
        *,
        account_id: str | None = None,
    ) -> CleaningTask | None:
        """Putzauftrag anhand Buchungsnummer (für Stornierungs-Verknüpfung)."""
        query = with_account_filter({"booking_number": booking_number}, account_id)
        doc = self._col.find_one(query)
        return None if doc is None else CleaningTask.from_mongo(doc)

    def list_tasks(
        self,
        *,
        account_id: str | None = None,
        status: str | None = None,
        property_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CleaningTask]:
        """Putzaufträge filtern (Status / Wohnung / Putztermin-Zeitraum)."""
        base: dict[str, Any] = {}
        if status:
            base["status"] = status
        if property_name and property_name.strip():
            base["property_name"] = property_name.strip()
        date_filter: dict[str, str] = {}
        if date_from is not None:
            date_filter["$gte"] = date_from.isoformat()
        if date_to is not None:
            date_filter["$lte"] = date_to.isoformat()
        if date_filter:
            base["cleaning_date"] = date_filter
        query = with_account_filter(base, account_id)
        cursor = self._col.find(query).sort("cleaning_date", 1)
        return [CleaningTask.from_mongo(doc) for doc in cursor]

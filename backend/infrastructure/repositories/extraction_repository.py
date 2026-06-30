"""Persistenz von Extraktionen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from pymongo.collection import Collection

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


@dataclass(frozen=True)
class ExtractionSnapshot:
    """Extraktion inkl. Metadaten aus einem Mongo-Dokument."""

    extraction: BookingExtraction
    workflow_id: str | None = None


class ExtractionRepository:
    """Collection `extractions`."""

    COLLECTION = "extractions"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def save(
        self,
        correlation_id: str,
        message_id: str,
        extraction: BookingExtraction,
        *,
        account_id: str | None = None,
        workflow_id: str | None = None,
        workflow_slug: str | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> None:
        """Extraktion speichern."""
        doc: dict[str, Any] = {
            "_id": correlation_id,
            "message_id": message_id,
            "extraction": extraction.model_dump(mode="json"),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if account_id:
            doc["account_id"] = account_id
        if workflow_id:
            doc["workflow_id"] = workflow_id
        if workflow_slug:
            doc["workflow_slug"] = workflow_slug
        if custom_fields is not None:
            doc["custom_fields"] = custom_fields
        self._col.update_one({"_id": correlation_id}, {"$set": doc}, upsert=True)

    def get_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> BookingExtraction | None:
        """Extraktion laden."""
        query = with_account_filter({"_id": correlation_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None and account_id:
            doc = self._col.find_one({"_id": correlation_id})
            if doc and doc.get("account_id") not in (None, account_id):
                return None
        if doc is None or "extraction" not in doc:
            return None
        return BookingExtraction.model_validate(doc["extraction"])

    def map_by_correlation_ids(
        self,
        correlation_ids: list[str],
        *,
        account_id: str | None = None,
    ) -> dict[str, BookingExtraction]:
        """Lädt Extraktionen in einem Query."""
        return {
            cid: snap.extraction
            for cid, snap in self.map_snapshots_by_correlation_ids(
                correlation_ids,
                account_id=account_id,
            ).items()
        }

    def map_snapshots_by_correlation_ids(
        self,
        correlation_ids: list[str],
        *,
        account_id: str | None = None,
    ) -> dict[str, ExtractionSnapshot]:
        """Lädt Extraktionen inkl. workflow_id in einem Query."""
        if not correlation_ids:
            return {}
        unique_ids = list(dict.fromkeys(correlation_ids))
        query = with_account_filter({"_id": {"$in": unique_ids}}, account_id)
        result: dict[str, ExtractionSnapshot] = {}
        for doc in self._col.find(query):
            doc_account = doc.get("account_id")
            if account_id and doc_account not in (None, account_id):
                continue
            if "extraction" not in doc:
                continue
            cid = str(doc["_id"])
            wf = doc.get("workflow_id")
            workflow_id = str(wf) if wf else None
            result[cid] = ExtractionSnapshot(
                extraction=BookingExtraction.model_validate(doc["extraction"]),
                workflow_id=workflow_id,
            )
        return result

    def list_future_bookings(
        self,
        *,
        account_id: str | None = None,
        checkout_from: date,
    ) -> list[tuple[str, BookingExtraction]]:
        """Neubuchungen/Änderungen mit Check-out ab einem Datum (für Backfill)."""
        base: dict[str, Any] = {
            "extraction.check_out": {"$gte": checkout_from.isoformat()},
            "extraction.intent": {"$in": ["new_booking", "change"]},
        }
        query = with_account_filter(base, account_id)
        result: list[tuple[str, BookingExtraction]] = []
        for doc in self._col.find(query):
            if account_id and doc.get("account_id") not in (None, account_id):
                continue
            if "extraction" not in doc:
                continue
            result.append(
                (str(doc["_id"]), BookingExtraction.model_validate(doc["extraction"]))
            )
        return result

    def get_workflow_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> str | None:
        """Tenant-Workflow-ID falls gesetzt."""
        query = with_account_filter({"_id": correlation_id}, account_id)
        doc = self._col.find_one(query, {"workflow_id": 1})
        if doc is None and account_id:
            doc = self._col.find_one({"_id": correlation_id}, {"workflow_id": 1})
            if doc and doc.get("account_id") not in (None, account_id):
                return None
        if doc is None:
            return None
        wf = doc.get("workflow_id")
        return str(wf) if wf else None

    def get_custom_fields(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Custom-Felder aus Tenant-Workflow-Extraktion."""
        query = with_account_filter({"_id": correlation_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None and account_id:
            doc = self._col.find_one({"_id": correlation_id})
            if doc and doc.get("account_id") not in (None, account_id):
                return None
        if doc is None:
            return None
        custom = doc.get("custom_fields")
        return custom if isinstance(custom, dict) else None

    def list_correlation_ids_by_workflow_slug(
        self,
        workflow_slug: str,
        *,
        account_id: str | None = None,
        limit: int = 2000,
    ) -> list[str]:
        """Correlation-IDs mit Tenant-Workflow-Zuordnung."""
        query = with_account_filter({"workflow_slug": workflow_slug}, account_id)
        cursor = (
            self._col.find(query, {"_id": 1})
            .sort("updated_at", -1)
            .limit(max(limit, 1))
        )
        return [str(doc["_id"]) for doc in cursor]

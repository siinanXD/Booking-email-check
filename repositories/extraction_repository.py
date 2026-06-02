"""Persistenz von Extraktionen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from repositories.mongo import Db
from schemas.booking.extraction import BookingExtraction


class ExtractionRepository:
    """Collection `extractions`."""

    COLLECTION = "extractions"

    def __init__(self, db: Db) -> None:
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    def save(
        self,
        correlation_id: str,
        message_id: str,
        extraction: BookingExtraction,
    ) -> None:
        """Extraktion speichern."""
        doc = {
            "_id": correlation_id,
            "message_id": message_id,
            "extraction": extraction.model_dump(mode="json"),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._col.update_one({"_id": correlation_id}, {"$set": doc}, upsert=True)

    def get_by_correlation_id(self, correlation_id: str) -> BookingExtraction | None:
        """Extraktion laden."""
        doc = self._col.find_one({"_id": correlation_id})
        if doc is None or "extraction" not in doc:
            return None
        return BookingExtraction.model_validate(doc["extraction"])

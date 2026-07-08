"""Dedupe-Marker für geplante WhatsApp-Berichte (einmal pro Woche)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from backend.infrastructure.repositories.mongo import Db


class WhatsAppReportMarkerRepository:
    """Collection `whatsapp_report_markers`.

    Ein Dokument pro (account_id, job, period_key). `try_claim` ist
    idempotent: nur der erste Aufruf pro Periode gewinnt — so wird ein
    Bericht auch bei mehreren Workern/Restarts genau einmal versendet.
    """

    COLLECTION = "whatsapp_report_markers"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index(
            [("account_id", 1), ("job", 1), ("period_key", 1)],
            unique=True,
        )

    def try_claim(self, *, account_id: str, job: str, period_key: str) -> bool:
        """True wenn der Bericht für diese Periode noch nicht versendet wurde."""
        try:
            self._col.insert_one(
                {
                    "account_id": account_id,
                    "job": job,
                    "period_key": period_key,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            return True
        except DuplicateKeyError:
            return False

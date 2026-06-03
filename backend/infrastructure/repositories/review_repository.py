"""Persistenz von Review-Entwürfen und Freigabe-Status."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from backend.core.models.response import ReviewStatus
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.tenant_scope import with_account_filter


class ReviewRecord(BaseModel):
    """Gespeicherter Review-Stand für die Web-API."""

    correlation_id: str
    message_id: str
    draft_body: str = ""
    grounding_flag: bool = False
    review_status: str = "pending"
    reviewer_note: str | None = None
    approved_body: str | None = None
    intent: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewRepository:
    """Collection `reviews`."""

    COLLECTION = "reviews"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index(
            [("review_status", 1), ("account_id", 1), ("updated_at", -1)],
            name="idx_review_status_account_updated",
        )

    def upsert_pending(
        self,
        *,
        correlation_id: str,
        message_id: str,
        draft_body: str,
        grounding_flag: bool,
        intent: str | None,
        account_id: str | None = None,
    ) -> ReviewRecord:
        """Speichert ausstehenden Review-Entwurf."""
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "_id": correlation_id,
            "correlation_id": correlation_id,
            "message_id": message_id,
            "draft_body": draft_body,
            "grounding_flag": grounding_flag,
            "review_status": "pending",
            "intent": intent,
            "updated_at": now.isoformat(),
        }
        if account_id:
            doc["account_id"] = account_id
        self._col.update_one({"_id": correlation_id}, {"$set": doc}, upsert=True)
        return self.get(
            correlation_id, account_id=account_id
        ) or ReviewRecord.model_validate(doc)

    def update_status(
        self,
        correlation_id: str,
        status: str,
        *,
        account_id: str | None = None,
        approved_body: str | None = None,
        reviewer_note: str | None = None,
    ) -> ReviewRecord | None:
        """Aktualisiert Review-Status nach Freigabe/Ablehnung."""
        update: dict[str, Any] = {
            "review_status": status,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if approved_body is not None:
            update["approved_body"] = approved_body
        if reviewer_note is not None:
            update["reviewer_note"] = reviewer_note
        query = with_account_filter({"_id": correlation_id}, account_id)
        self._col.update_one(query, {"$set": update})
        return self.get(correlation_id, account_id=account_id)

    def get(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> ReviewRecord | None:
        """Lädt einen Review-Datensatz."""
        query = with_account_filter({"_id": correlation_id}, account_id)
        doc = self._col.find_one(query)
        if doc is None:
            return None
        return ReviewRecord.model_validate(doc)

    def count_pending(self, *, account_id: str | None = None) -> int:
        """Anzahl ausstehender Reviews."""
        query = with_account_filter({"review_status": "pending"}, account_id)
        return int(self._col.count_documents(query))

    def list_pending(
        self,
        limit: int = 50,
        *,
        account_id: str | None = None,
    ) -> list[ReviewRecord]:
        """Ausstehende Reviews, neueste zuerst."""
        query = with_account_filter({"review_status": "pending"}, account_id)
        cursor = self._col.find(query).sort("updated_at", -1).limit(limit)
        return [ReviewRecord.model_validate(doc) for doc in cursor]

    def save(
        self,
        review: ReviewStatus,
        *,
        message_id: str,
        draft_body: str = "",
        grounding_flag: bool = False,
        intent: str | None = None,
        account_id: str | None = None,
    ) -> ReviewRecord:
        """Alias: persistiert ReviewStatus (pending oder finaler Status)."""
        if review.status == "pending":
            return self.upsert_pending(
                correlation_id=review.correlation_id,
                message_id=message_id,
                draft_body=draft_body,
                grounding_flag=grounding_flag,
                intent=intent,
                account_id=account_id,
            )
        record = self.update_status(
            review.correlation_id,
            review.status,
            account_id=account_id,
            approved_body=review.approved_body,
            reviewer_note=review.reviewer_note,
        )
        if record is not None:
            return record
        return ReviewRecord(
            correlation_id=review.correlation_id,
            message_id=message_id,
            draft_body=draft_body,
            grounding_flag=grounding_flag,
            review_status=review.status,
            reviewer_note=review.reviewer_note,
            approved_body=review.approved_body,
            intent=intent,
        )

    def get_by_correlation_id(
        self,
        correlation_id: str,
        *,
        account_id: str | None = None,
    ) -> ReviewStatus | None:
        """Alias: lädt ReviewStatus für correlation_id."""
        record = self.get(correlation_id, account_id=account_id)
        if record is None:
            return None
        return _record_to_status(record)

    def list_pending_statuses(
        self,
        limit: int = 50,
        *,
        account_id: str | None = None,
    ) -> list[ReviewStatus]:
        """Alias: ausstehende Reviews als ReviewStatus."""
        return [
            _record_to_status(record)
            for record in self.list_pending(limit, account_id=account_id)
        ]

    def mark_approved(
        self,
        correlation_id: str,
        approved_body: str,
        *,
        account_id: str | None = None,
    ) -> ReviewRecord | None:
        """Alias: markiert Review als freigegeben."""
        return self.update_status(
            correlation_id,
            "approved",
            account_id=account_id,
            approved_body=approved_body,
        )

    def mark_rejected(
        self,
        correlation_id: str,
        reason: str,
        *,
        account_id: str | None = None,
    ) -> ReviewRecord | None:
        """Alias: markiert Review als abgelehnt."""
        return self.update_status(
            correlation_id,
            "rejected",
            account_id=account_id,
            reviewer_note=reason,
        )


def _record_to_status(record: ReviewRecord) -> ReviewStatus:
    return ReviewStatus(
        correlation_id=record.correlation_id,
        status=record.review_status,
        reviewer_note=record.reviewer_note,
        approved_body=record.approved_body,
    )

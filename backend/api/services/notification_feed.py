"""Leitet das Glocken-Feed aus aktuellen Mails ab (kein eigener Schreibpfad).

Der Lesestatus wird je Account in der Collection ``notification_state`` als
Zeitstempel gehalten: alles, was nach ``read_at`` eingegangen ist, gilt als
ungelesen. So bleibt das Feed konsistent mit den realen Daten, ohne eine
zusätzliche, fehleranfällige Outbox pflegen zu müssen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.api.schemas.notifications import NotificationItem, NotificationsResponse
from backend.core.models.email import ProcessingState

_STATE_COLLECTION = "notification_state"
_FEED_LIMIT = 20


def _read_at(db: Any, account_id: str) -> str:
    doc = db[_STATE_COLLECTION].find_one({"_id": account_id})
    if doc:
        value = doc.get("read_at")
        if isinstance(value, str):
            return value
    return ""


def mark_all_read(db: Any, account_id: str) -> None:
    """Setzt den Lese-Zeitstempel des Accounts auf jetzt."""
    now = datetime.now(UTC).isoformat()
    db[_STATE_COLLECTION].update_one(
        {"_id": account_id},
        {"$set": {"read_at": now, "account_id": account_id}},
        upsert=True,
    )


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else ""


def _item_for(email: Any) -> NotificationItem | None:
    created = _iso(getattr(email, "received_at", None))
    cid = getattr(email, "correlation_id", "")
    subject = (getattr(email, "subject", "") or "Mail").strip()
    state = getattr(email, "processing_state", None)
    intent = getattr(email, "effective_intent", None)
    review_status = getattr(email, "review_status", None)

    if review_status == "escalated":
        return NotificationItem(
            id=f"esc:{cid}",
            kind="escalation",
            title=f"Eskaliert · {subject}",
            created_at=created,
            href="/review",
        )
    if state == ProcessingState.PENDING_REVIEW:
        return NotificationItem(
            id=f"rev:{cid}",
            kind="review_waiting",
            title="Review wartet",
            detail=subject,
            created_at=created,
            href="/review",
        )
    if intent == "new_booking":
        return NotificationItem(
            id=f"book:{cid}",
            kind="new_booking",
            title="Neue Buchung",
            detail=subject,
            created_at=created,
            href="/inbox?intent=new_booking",
        )
    return None


def build_feed(ctx: Any, account_id: str) -> NotificationsResponse:
    """Erzeugt das Glocken-Feed für einen Account."""
    emails, _ = ctx.email_repo.list_filtered(account_id=account_id, limit=_FEED_LIMIT)
    read_at = _read_at(ctx.db, account_id)
    items: list[NotificationItem] = []
    for email in emails:
        item = _item_for(email)
        if item is None:
            continue
        item.read = bool(read_at) and item.created_at <= read_at
        items.append(item)
    unread = sum(1 for item in items if not item.read)
    return NotificationsResponse(items=items, unread=unread)

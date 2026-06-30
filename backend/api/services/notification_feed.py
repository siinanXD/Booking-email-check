"""Leitet das Glocken-Feed aus aktuellen Mails ab (kein eigener Schreibpfad).

Der Lesestatus wird **je Benutzer** in der Collection ``notification_state`` als
Zeitstempel gehalten (Schlüssel = user_id): alles, was nach ``read_at``
eingegangen ist, gilt als ungelesen. So markiert nicht ein Team-Mitglied alles
für alle gelesen. Das Feed selbst bleibt account-scoped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.api.schemas.notifications import NotificationItem, NotificationsResponse
from backend.core.models.email import ProcessingState

_STATE_COLLECTION = "notification_state"
_FEED_LIMIT = 20


def _read_at(db: Any, user_id: str) -> str:
    doc = db[_STATE_COLLECTION].find_one({"_id": user_id})
    if doc:
        value = doc.get("read_at")
        if isinstance(value, str):
            return value
    return ""


def mark_all_read(db: Any, user_id: str) -> None:
    """Setzt den Lese-Zeitstempel des Benutzers auf jetzt."""
    now = datetime.now(UTC).isoformat()
    db[_STATE_COLLECTION].update_one(
        {"_id": user_id},
        {"$set": {"read_at": now, "user_id": user_id}},
        upsert=True,
    )


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else ""


def _item_for(email: Any, escalated_cids: set[str]) -> NotificationItem | None:
    created = _iso(getattr(email, "received_at", None))
    cid = getattr(email, "correlation_id", "")
    subject = (getattr(email, "subject", "") or "Mail").strip()
    state = getattr(email, "processing_state", None)
    intent = getattr(email, "effective_intent", None)

    if cid in escalated_cids:
        return None  # bereits als Eskalation gelistet
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


def _escalation_items(
    ctx: Any, account_id: str, subjects: dict[str, str]
) -> list[NotificationItem]:
    """Eskalierte offene Reviews (Eskalation liegt auf dem Review-Datensatz)."""
    items: list[NotificationItem] = []
    for record in ctx.review_repo.list_pending(
        limit=_FEED_LIMIT, account_id=account_id
    ):
        if not getattr(record, "escalated", False):
            continue
        cid = record.correlation_id
        subject = subjects.get(cid) or "Mail"
        items.append(
            NotificationItem(
                id=f"esc:{cid}",
                kind="escalation",
                title=f"Eskaliert · {subject}",
                created_at=_iso(record.updated_at),
                href="/review",
            )
        )
    return items


def build_feed(ctx: Any, account_id: str, user_id: str) -> NotificationsResponse:
    """Erzeugt das Glocken-Feed für einen Account (Lesestatus je Benutzer)."""
    emails, _ = ctx.email_repo.list_filtered(account_id=account_id, limit=_FEED_LIMIT)
    subjects = {e.correlation_id: (e.subject or "Mail").strip() for e in emails}
    read_at = _read_at(ctx.db, user_id)

    escalations = _escalation_items(ctx, account_id, subjects)
    escalated_cids = {e.id.split(":", 1)[1] for e in escalations}

    items: list[NotificationItem] = list(escalations)
    for email in emails:
        item = _item_for(email, escalated_cids)
        if item is not None:
            items.append(item)

    for item in items:
        item.read = bool(read_at) and item.created_at <= read_at
    unread = sum(1 for item in items if not item.read)
    return NotificationsResponse(items=items[:_FEED_LIMIT], unread=unread)

"""Admin-Einzel-Trace: Aktivitäts-Timeline einer Mail mit Entscheidungs-Detail."""

from __future__ import annotations

from datetime import datetime

from backend.api.schemas.emails import EmailActivityEvent, EmailActivityResponse
from backend.api.services.email_activity_queries import get_email_activity
from backend.core.config.factory import AppContext
from backend.core.models.notification import NotificationStatus
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)

_FAILED_LABELS = {
    NotificationStatus.FAILED: "WhatsApp fehlgeschlagen",
    NotificationStatus.SKIPPED: "WhatsApp übersprungen",
}


def admin_mail_trace(
    ctx: AppContext, account_id: str, correlation_id: str
) -> EmailActivityResponse | None:
    """Reichert die Timeline (cross-tenant) mit Entscheidungs- + Versanddetail an."""
    base = get_email_activity(ctx, account_id, correlation_id)
    if base is None:
        return None

    review = ctx.review_repo.get(correlation_id, account_id=account_id)
    for event in base.events:
        if event.kind.startswith("review_") and review is not None:
            event.intent = review.intent
            event.confidence = review.confidence
            event.auto_approved = review.auto_approved
            event.escalated = review.escalated
        elif event.kind == "whatsapp_sent":
            event.notification_status = NotificationStatus.SENT.value

    for notification in NotificationRepository(ctx.db).list_by_correlation_id(
        correlation_id
    ):
        if notification.status not in _FAILED_LABELS:
            continue
        stamp = notification.sent_at or notification.created_at
        at = stamp.isoformat() if isinstance(stamp, datetime) else str(stamp)
        base.events.append(
            EmailActivityEvent(
                at=at,
                kind=f"whatsapp_{notification.status.value}",
                label=_FAILED_LABELS[notification.status],
                notification_status=notification.status.value,
                error=notification.error,
            )
        )

    base.events.sort(key=lambda event: event.at)
    return base

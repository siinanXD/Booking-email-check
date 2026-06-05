"""Arbeitsverlauf für eine E-Mail-Correlation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.api.schemas.emails import EmailActivityEvent, EmailActivityResponse
from backend.core.config.factory import AppContext
from backend.core.models.notification import NotificationKind, NotificationStatus
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)

_REVIEW_EVENTS: dict[str, tuple[str, str]] = {
    "pending": ("review_created", "Review angelegt"),
    "approved": ("review_approved", "Freigegeben"),
    "rejected": ("review_rejected", "Abgelehnt"),
    "completed": ("review_completed", "Abgeschlossen"),
}

_NOTIFICATION_LABELS: dict[NotificationKind, str] = {
    NotificationKind.BOOKING_CLEANING_TASK: "WhatsApp: Reinigungsauftrag gesendet",
    NotificationKind.BOOKING_STATUS_NOTICE: "WhatsApp: Statusmitteilung gesendet",
    NotificationKind.BOOKING_GUEST_INQUIRY: "WhatsApp: Gästeanfrage gesendet",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _coerce_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def get_email_activity(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
) -> EmailActivityResponse | None:
    """Baut Timeline aus E-Mails, Reviews und Benachrichtigungen."""
    email = ctx.email_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if email is None:
        return None

    events: list[EmailActivityEvent] = []
    for mail in ctx.email_repo.list_by_correlation_id(
        correlation_id,
        account_id=account_id,
    ):
        received_at = _iso(mail.received_at)
        if received_at:
            events.append(
                EmailActivityEvent(
                    at=received_at,
                    kind="mail_received",
                    label="Mail empfangen",
                )
            )

    extraction = ctx.extraction_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if extraction is not None:
        extraction_at = (
            _coerce_iso(email.updated_at)
            or _iso(email.received_at)
            or datetime.now().astimezone().isoformat()
        )
        events.append(
            EmailActivityEvent(
                at=extraction_at,
                kind="extraction_done",
                label="Extraktion abgeschlossen",
            )
        )

    review = ctx.review_repo.get(correlation_id, account_id=account_id)
    if review is not None:
        review_at = (
            _coerce_iso(review.updated_at)
            or _iso(email.received_at)
            or datetime.now().astimezone().isoformat()
        )
        kind, label = _REVIEW_EVENTS.get(
            review.review_status,
            ("review_updated", "Review aktualisiert"),
        )
        events.append(
            EmailActivityEvent(
                at=review_at,
                kind=kind,
                label=label,
            )
        )

    notification_repo = NotificationRepository(ctx.db)
    for notification in notification_repo.list_by_correlation_id(correlation_id):
        if notification.status != NotificationStatus.SENT:
            continue
        fallback_at = (
            _coerce_iso(review.updated_at)
            if review is not None
            else _iso(email.received_at)
        )
        sent_at = (
            _iso(notification.sent_at) or _iso(notification.created_at) or fallback_at
        )
        if not sent_at:
            continue
        events.append(
            EmailActivityEvent(
                at=sent_at,
                kind="whatsapp_sent",
                label=_NOTIFICATION_LABELS.get(
                    notification.kind,
                    "WhatsApp-Nachricht gesendet",
                ),
            )
        )

    events.sort(key=lambda event: event.at)
    return EmailActivityResponse(correlation_id=correlation_id, events=events)

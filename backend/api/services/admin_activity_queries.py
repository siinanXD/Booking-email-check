"""Plattform-Admin: operativer Aktivitäts-Überblick (Mails + WhatsApp)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from backend.core.config.factory import AppContext
from backend.core.models.email import ProcessingState

_STATUS_KEYS = ("sent", "failed", "skipped", "pending")
_MAIL_STATE_KEYS = (
    ProcessingState.PENDING_REVIEW,
    ProcessingState.APPROVED,
    ProcessingState.REJECTED,
    ProcessingState.DISCARDED,
)


class ActivityNotification(BaseModel):
    """Ein WhatsApp-Sendeversuch für die Admin-Ansicht."""

    id: str
    created_at: datetime
    kind: str
    recipient_masked: str
    status: str
    error: str | None = None
    tenant: str | None = None


class ActivityMail(BaseModel):
    """Eine verarbeitete Kunden-Mail für die Admin-Ansicht."""

    correlation_id: str
    subject: str
    intent: str | None = None
    processing_state: str
    at: datetime | None = None
    tenant: str | None = None


class ActivityResponse(BaseModel):
    """Operativer Aktivitäts-Überblick."""

    generated_at: datetime
    notification_counts_24h: dict[str, int]
    notification_counts_7d: dict[str, int]
    mail_counts_24h: dict[str, int]
    recent_notifications: list[ActivityNotification]
    recent_mails: list[ActivityMail]


def _mask_phone(e164: str) -> str:
    digits = e164.strip()
    if len(digits) <= 4:
        return "••••"
    return f"{digits[:3]}••••{digits[-2:]}"


def _normalize_counts(raw: dict[str, int]) -> dict[str, int]:
    return {key: int(raw.get(key, 0)) for key in _STATUS_KEYS}


class _TenantNames:
    """Cache für Mandanten-Anzeigenamen (account_id → display_name)."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        self._cache: dict[str, str | None] = {}

    def get(self, account_id: str | None) -> str | None:
        if not account_id:
            return None
        if account_id not in self._cache:
            account = self._ctx.account_repo.get_by_id(account_id)
            self._cache[account_id] = account.display_name if account else None
        return self._cache[account_id]


def admin_activity(
    ctx: AppContext,
    *,
    notif_limit: int = 50,
    mail_limit: int = 50,
) -> ActivityResponse:
    """Sammelt WhatsApp-Sends und verarbeitete Mails mandantenübergreifend."""
    now = datetime.now(UTC)
    since_24h = (now - timedelta(hours=24)).isoformat()
    since_7d = (now - timedelta(days=7)).isoformat()
    names = _TenantNames(ctx)

    # WhatsApp-Sends + Status-Zähler
    notifications = ctx.notification_repo.list_recent(notif_limit)
    corr_ids = [n.correlation_id for n in notifications]
    corr_to_account: dict[str, str | None] = {}
    for mail in ctx.email_repo.list_by_correlation_ids(corr_ids, account_id=None):
        corr_to_account.setdefault(mail.correlation_id, mail.account_id)

    recent_notifications = [
        ActivityNotification(
            id=n.id,
            created_at=n.created_at,
            kind=n.kind.value,
            recipient_masked=_mask_phone(n.recipient_e164),
            status=n.status.value,
            error=n.error,
            tenant=names.get(corr_to_account.get(n.correlation_id)),
        )
        for n in notifications
    ]

    # Verarbeitete Mails (mandantenübergreifend)
    mails, _total = ctx.email_repo.list_filtered(account_id=None, limit=mail_limit)
    recent_mails = [
        ActivityMail(
            correlation_id=m.correlation_id,
            subject=m.subject or "(kein Betreff)",
            intent=m.effective_intent,
            processing_state=m.processing_state.value,
            at=m.updated_at or m.received_at,
            tenant=names.get(m.account_id),
        )
        for m in mails
    ]

    mail_counts = {
        state.value: ctx.email_repo.count_by_state_since(
            state, since_24h, account_id=None
        )
        for state in _MAIL_STATE_KEYS
    }
    mail_counts["total"] = ctx.email_repo.count_updated_since(
        since_24h, account_id=None
    )

    return ActivityResponse(
        generated_at=now,
        notification_counts_24h=_normalize_counts(
            ctx.notification_repo.count_by_status(since_24h)
        ),
        notification_counts_7d=_normalize_counts(
            ctx.notification_repo.count_by_status(since_7d)
        ),
        mail_counts_24h=mail_counts,
        recent_notifications=recent_notifications,
        recent_mails=recent_mails,
    )

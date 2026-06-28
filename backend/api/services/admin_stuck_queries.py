"""Admin-Stuck/Fehler-Liste: hängende Verarbeitung + verworfene Mails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.api.schemas.admin_pipeline import AdminStuckItem, AdminStuckResponse
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail

# Nicht-terminale Verarbeitungs-Zustände (kein pending_review, keine terminalen).
_NON_TERMINAL = [
    "received",
    "triaged",
    "classified",
    "extracted",
    "validated",
    "retrieved",
    "drafted",
]


class _Names:
    """account_id → display_name (memoisiert)."""

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


def _age_hours(updated_at: object, now: datetime) -> int:
    if isinstance(updated_at, datetime):
        when = updated_at
    elif isinstance(updated_at, str) and updated_at:
        try:
            when = datetime.fromisoformat(updated_at)
        except ValueError:
            return 0
    else:
        return 0
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0, int((now - when).total_seconds() // 3600))


def _item(
    mail: StoredEmail, names: _Names, now: datetime, *, reason: bool
) -> AdminStuckItem:
    updated = mail.updated_at
    updated_iso = (
        updated.isoformat() if isinstance(updated, datetime) else (updated or None)
    )
    return AdminStuckItem(
        correlation_id=mail.correlation_id,
        account_id=mail.account_id,
        tenant=names.get(mail.account_id),
        subject=mail.subject or "(kein Betreff)",
        processing_state=mail.processing_state.value,
        updated_at=updated_iso,
        age_hours=_age_hours(updated, now),
        reason=mail.triage_outcome if reason else None,
    )


def admin_stuck_mails(ctx: AppContext, *, hours: int, kind: str) -> AdminStuckResponse:
    """processing = hängend (älter als `hours`); discarded = jüngste verworfene."""
    now = datetime.now(UTC)
    names = _Names(ctx)
    if kind == "discarded":
        mails, _ = ctx.email_repo.list_filtered(
            account_id=None, status="discarded", limit=100
        )
        items = [_item(m, names, now, reason=True) for m in mails]
    else:
        kind = "processing"
        cutoff = (now - timedelta(hours=hours)).isoformat()
        mails = ctx.email_repo.list_stuck(
            _NON_TERMINAL, cutoff, account_id=None, limit=100
        )
        items = [_item(m, names, now, reason=False) for m in mails]
    return AdminStuckResponse(kind=kind, items=items, total=len(items))

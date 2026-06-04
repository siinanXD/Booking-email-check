"""Shared helpers for admin overview and metrics queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from backend.api.schemas.accounts import AccountListItem
from backend.api.schemas.admin_overview import MailConnectionSummary
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.infrastructure.observability.langfuse_setup import tracing_enabled
from backend.infrastructure.repositories.account_repository import AccountRecord
from backend.infrastructure.repositories.domain_collections import (
    BOOKINGS,
    CHUNKS,
    CONVERSATIONS,
    EMAILS,
    EMBEDDINGS,
    GUESTS,
    PROPERTIES,
)
from backend.infrastructure.repositories.tenant_scope import with_account_filter

ActivityStatus = Literal["active", "idle", "never"]

_DB_COUNT_COLLECTIONS = (
    EMAILS,
    BOOKINGS,
    GUESTS,
    PROPERTIES,
    CONVERSATIONS,
    CHUNKS,
    EMBEDDINGS,
    "reviews",
)


def period(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    return start, end


def langfuse_session_url(
    settings: Settings,
    correlation_id: str | None,
) -> str | None:
    if not correlation_id or not tracing_enabled(settings):
        return None
    host = settings.langfuse_host.rstrip("/")
    project_id = (settings.langfuse_project_id or "").strip()
    if project_id:
        return f"{host}/project/{project_id}/sessions/{correlation_id}"
    return f"{host}/sessions/{correlation_id}"


def activity_status(
    *,
    last_sync_at: datetime | None,
    last_email_received_at: str | None,
    last_review_at: str | None,
    has_metric_7d: bool,
    has_any_metric: bool = False,
    now: datetime | None = None,
) -> ActivityStatus:
    """Heuristik: active / idle / never."""
    now = now or datetime.now(UTC)
    sync_cutoff = now - timedelta(days=7)
    review_cutoff = now - timedelta(days=30)

    if last_sync_at is not None and last_sync_at >= sync_cutoff:
        return "active"
    if last_email_received_at:
        try:
            received = datetime.fromisoformat(
                last_email_received_at.replace("Z", "+00:00")
            )
            if received.tzinfo is None:
                received = received.replace(tzinfo=UTC)
            if received >= sync_cutoff:
                return "active"
        except ValueError:
            pass
    if last_review_at:
        try:
            reviewed = datetime.fromisoformat(last_review_at.replace("Z", "+00:00"))
            if reviewed.tzinfo is None:
                reviewed = reviewed.replace(tzinfo=UTC)
            if reviewed >= review_cutoff:
                return "active"
        except ValueError:
            pass
    if has_metric_7d:
        return "active"

    has_any_signal = (
        last_sync_at is not None
        or bool(last_email_received_at)
        or bool(last_review_at)
        or has_metric_7d
        or has_any_metric
    )
    return "idle" if has_any_signal else "never"


def to_list_item(account: AccountRecord) -> AccountListItem:
    return AccountListItem(
        id=account.id,
        display_name=account.display_name,
        contact_email=account.contact_email,
        account_type=account.account_type,
        company_name=account.company_name,
        phone=account.phone,
        status=account.status,
        rejection_reason=account.rejection_reason,
        created_at=account.created_at.isoformat(),
    )


def mail_summary(ctx: AppContext, account_id: str) -> MailConnectionSummary | None:
    conn = ctx.mail_connection_repo.get(account_id)
    if conn is None:
        return None
    return MailConnectionSummary(
        provider=conn.provider,
        status=conn.status,
        email_address=conn.email_address,
        connected=conn.status == "connected",
        last_sync_at=conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        last_error=conn.last_error,
        onboarding_completed=conn.onboarding_completed,
    )


def db_counts(ctx: AppContext, account_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in _DB_COUNT_COLLECTIONS:
        query = with_account_filter({}, account_id)
        counts[name] = int(ctx.db[name].count_documents(query))
    return counts


def account_tokens(
    ctx: AppContext,
    account_id: str,
    start: datetime,
    end: datetime,
) -> int:
    pipeline: list[dict[str, Any]] = [
        {
            "$match": {
                "account_id": account_id,
                "processed_at": {
                    "$gte": start.isoformat(),
                    "$lte": end.isoformat(),
                },
            }
        },
        {
            "$group": {
                "_id": None,
                "prompt_tokens": {"$sum": "$prompt_tokens"},
                "completion_tokens": {"$sum": "$completion_tokens"},
            }
        },
    ]
    rows = list(ctx.metrics_repo._col.aggregate(pipeline))
    if not rows:
        return 0
    return int(rows[0].get("prompt_tokens", 0)) + int(
        rows[0].get("completion_tokens", 0)
    )


def tenant_activity(
    ctx: AppContext, account_id: str, start_7d: datetime
) -> ActivityStatus:
    mail = ctx.mail_connection_repo.get(account_id)
    last_sync = mail.last_sync_at if mail else None
    last_email = ctx.email_repo.max_received_at(account_id=account_id)
    last_review = ctx.review_repo.max_updated_at(account_id=account_id)
    has_metric = ctx.metrics_repo.has_metric_since(
        start_7d.isoformat(), account_id=account_id
    )
    has_any_metric = ctx.metrics_repo.has_any_for_account(account_id)
    return activity_status(
        last_sync_at=last_sync,
        last_email_received_at=last_email,
        last_review_at=last_review,
        has_metric_7d=has_metric,
        has_any_metric=has_any_metric,
    )

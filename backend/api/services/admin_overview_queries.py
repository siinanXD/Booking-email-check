"""Cross-Tenant Admin-Monitoring-Queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from backend.api.schemas.accounts import AccountListItem
from backend.api.schemas.admin_overview import (
    AdminAccountCostRow,
    AdminAccountDetailResponse,
    AdminCostsMetricsResponse,
    AdminExpensiveMailRow,
    AdminOverviewResponse,
    AdminPublicConfigResponse,
    AdminTenantRow,
    AdminTokensMetricsResponse,
    AdminUserSummary,
    MailConnectionSummary,
)
from backend.api.schemas.costs import CostSeriesPoint
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


def _period(days: int) -> tuple[datetime, datetime]:
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


def _to_list_item(account: AccountRecord) -> AccountListItem:
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


def _mail_summary(ctx: AppContext, account_id: str) -> MailConnectionSummary | None:
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


def _account_tokens(
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


def _tenant_activity(
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


def admin_overview(ctx: AppContext, *, days: int = 30) -> AdminOverviewResponse:
    start, end = _period(days)
    start_7d, _ = _period(7)
    accounts = ctx.account_repo.list_by_status(None)
    platform = ctx.metrics_repo.aggregate_platform(start, end)

    pending = sum(1 for a in accounts if a.status == "pending")
    active = sum(1 for a in accounts if a.status == "active")

    cost_by_account = {
        row.get("account_id"): row
        for row in ctx.metrics_repo.sum_cost_by_account(start, end)
    }

    tenants: list[AdminTenantRow] = []
    active_users_7d = 0
    for account in accounts:
        if account.status != "active":
            continue
        act = _tenant_activity(ctx, account.id, start_7d)
        if act == "active":
            active_users_7d += 1
        metrics = cost_by_account.get(account.id, {})
        mail_conn = ctx.mail_connection_repo.get(account.id)
        tenants.append(
            AdminTenantRow(
                account=_to_list_item(account),
                activity_status=act,
                costs_30d_usd=float(metrics.get("cost_usd", 0.0)),
                tokens_30d=int(metrics.get("total_tokens", 0)),
                mails_processed_30d=int(metrics.get("mail_count", 0)),
                last_sync_at=(
                    mail_conn.last_sync_at.isoformat()
                    if mail_conn and mail_conn.last_sync_at
                    else None
                ),
                last_mail_received_at=ctx.email_repo.max_received_at(
                    account_id=account.id
                ),
            )
        )

    tenants.sort(key=lambda t: t.costs_30d_usd, reverse=True)

    return AdminOverviewResponse(
        total_accounts=len(accounts),
        pending_accounts=pending,
        active_accounts=active,
        active_users_7d=active_users_7d,
        total_cost_usd_30d=round(float(platform.get("cost_usd", 0.0)), 4),
        total_tokens_30d=int(platform.get("total_tokens", 0)),
        mails_processed_30d=int(platform.get("mail_count", 0)),
        tenants=tenants,
    )


def admin_account_detail(
    ctx: AppContext,
    account_id: str,
    settings: Settings,
    *,
    days: int = 30,
) -> AdminAccountDetailResponse | None:
    account = ctx.account_repo.get_by_id(account_id)
    if account is None:
        return None
    start, end = _period(days)
    start_7d, _ = _period(7)

    users = [
        AdminUserSummary(
            id=u.id,
            email=u.email,
            role=u.role,
            created_at=u.created_at.isoformat(),
        )
        for u in ctx.user_repo.list_by_account_id(account_id)
    ]

    cost = ctx.metrics_repo.sum_cost_between(start, end, account_id=account_id)
    mail_count = ctx.metrics_repo.count_between(start, end, account_id=account_id)
    tokens = _account_tokens(ctx, account_id, start, end)
    latest = ctx.metrics_repo.latest_for_account(account_id)
    correlation_id = latest.correlation_id if latest else None

    return AdminAccountDetailResponse(
        account=_to_list_item(account),
        users=users,
        mail_connection=_mail_summary(ctx, account_id),
        activity_status=_tenant_activity(ctx, account_id, start_7d),
        db_counts=db_counts(ctx, account_id),
        costs_30d_usd=round(cost, 4),
        tokens_30d=tokens,
        mails_processed_30d=mail_count,
        last_mail_received_at=ctx.email_repo.max_received_at(account_id=account_id),
        latest_correlation_id=correlation_id,
        langfuse_session_url=langfuse_session_url(settings, correlation_id),
    )


def admin_costs_metrics(
    ctx: AppContext,
    settings: Settings,
    *,
    days: int = 30,
) -> AdminCostsMetricsResponse:
    start, end = _period(days)
    series_raw = ctx.metrics_repo.aggregate_by_day(start, end, account_id=None)
    series = [CostSeriesPoint.model_validate(row) for row in series_raw]
    platform = ctx.metrics_repo.aggregate_platform(start, end)

    accounts = {a.id: a for a in ctx.account_repo.list_by_status(None)}
    by_account: list[AdminAccountCostRow] = []
    for row in ctx.metrics_repo.sum_cost_by_account(start, end):
        aid = row.get("account_id")
        if not isinstance(aid, str) or not aid:
            continue
        account = accounts.get(aid)
        by_account.append(
            AdminAccountCostRow(
                account_id=aid,
                display_name=account.display_name if account else aid,
                cost_usd=float(row.get("cost_usd", 0.0)),
                total_tokens=int(row.get("total_tokens", 0)),
                mail_count=int(row.get("mail_count", 0)),
            )
        )

    top_mails: list[AdminExpensiveMailRow] = []
    for metric in ctx.metrics_repo.top_expensive_between(start, end, limit=10):
        processed = metric.processed_at.isoformat()
        top_mails.append(
            AdminExpensiveMailRow(
                correlation_id=metric.correlation_id,
                account_id=metric.account_id,
                cost_usd=round(metric.cost_usd, 4),
                total_tokens=metric.prompt_tokens + metric.completion_tokens,
                processed_at=processed,
                langfuse_session_url=langfuse_session_url(
                    settings, metric.correlation_id
                ),
            )
        )

    return AdminCostsMetricsResponse(
        days=days,
        series=series,
        total_usd=round(float(platform.get("cost_usd", 0.0)), 4),
        by_account=by_account,
        top_mails=top_mails,
    )


def admin_tokens_metrics(
    ctx: AppContext, *, days: int = 30
) -> AdminTokensMetricsResponse:
    start, end = _period(days)
    platform = ctx.metrics_repo.aggregate_platform(start, end)
    accounts = {a.id: a for a in ctx.account_repo.list_by_status(None)}
    by_account: list[AdminAccountCostRow] = []
    for row in ctx.metrics_repo.sum_cost_by_account(start, end):
        aid = row.get("account_id")
        if not isinstance(aid, str) or not aid:
            continue
        account = accounts.get(aid)
        by_account.append(
            AdminAccountCostRow(
                account_id=aid,
                display_name=account.display_name if account else aid,
                cost_usd=float(row.get("cost_usd", 0.0)),
                total_tokens=int(row.get("total_tokens", 0)),
                mail_count=int(row.get("mail_count", 0)),
            )
        )
    return AdminTokensMetricsResponse(
        days=days,
        prompt_tokens=int(platform.get("prompt_tokens", 0)),
        completion_tokens=int(platform.get("completion_tokens", 0)),
        total_tokens=int(platform.get("total_tokens", 0)),
        by_account=by_account,
    )


def admin_public_config(settings: Settings) -> AdminPublicConfigResponse:
    project_id = (settings.langfuse_project_id or "").strip() or None
    return AdminPublicConfigResponse(
        langfuse_host=settings.langfuse_host,
        langfuse_project_id=project_id,
        langfuse_tracing_enabled=tracing_enabled(settings),
    )

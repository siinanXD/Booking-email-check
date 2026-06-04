"""Cross-Tenant Admin-Monitoring-Queries."""

from __future__ import annotations

from backend.api.schemas.admin_overview import (
    AdminAccountDetailResponse,
    AdminOverviewResponse,
    AdminPublicConfigResponse,
    AdminTenantRow,
    AdminUserSummary,
)
from backend.api.services.admin_overview_support import (
    ActivityStatus,
    account_tokens,
    activity_status,
    db_counts,
    langfuse_session_url,
    mail_summary,
    period,
    tenant_activity,
    to_list_item,
)
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.infrastructure.observability.langfuse_setup import tracing_enabled

__all__ = [
    "ActivityStatus",
    "activity_status",
    "admin_account_detail",
    "admin_costs_metrics",
    "admin_overview",
    "admin_public_config",
    "admin_tokens_metrics",
    "db_counts",
    "langfuse_session_url",
]


def admin_overview(ctx: AppContext, *, days: int = 30) -> AdminOverviewResponse:
    start, end = period(days)
    start_7d, _ = period(7)
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
        act = tenant_activity(ctx, account.id, start_7d)
        if act == "active":
            active_users_7d += 1
        metrics = cost_by_account.get(account.id, {})
        mail_conn = ctx.mail_connection_repo.get(account.id)
        tenants.append(
            AdminTenantRow(
                account=to_list_item(account),
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
    start, end = period(days)
    start_7d, _ = period(7)

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
    tokens = account_tokens(ctx, account_id, start, end)
    latest = ctx.metrics_repo.latest_for_account(account_id)
    correlation_id = latest.correlation_id if latest else None

    return AdminAccountDetailResponse(
        account=to_list_item(account),
        users=users,
        mail_connection=mail_summary(ctx, account_id),
        activity_status=tenant_activity(ctx, account_id, start_7d),
        db_counts=db_counts(ctx, account_id),
        costs_30d_usd=round(cost, 4),
        tokens_30d=tokens,
        mails_processed_30d=mail_count,
        last_mail_received_at=ctx.email_repo.max_received_at(account_id=account_id),
        latest_correlation_id=correlation_id,
        langfuse_session_url=langfuse_session_url(settings, correlation_id),
    )


def admin_public_config(settings: Settings) -> AdminPublicConfigResponse:
    project_id = (settings.langfuse_project_id or "").strip() or None
    return AdminPublicConfigResponse(
        langfuse_host=settings.langfuse_host,
        langfuse_project_id=project_id,
        langfuse_tracing_enabled=tracing_enabled(settings),
    )


from backend.api.services.admin_metrics_queries import (  # noqa: E402
    admin_costs_metrics,
    admin_tokens_metrics,
)

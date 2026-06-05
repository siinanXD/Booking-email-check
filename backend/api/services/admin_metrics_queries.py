"""Admin cost and token metrics queries."""

from __future__ import annotations

from backend.api.schemas.admin_overview import (
    AdminAccountCostRow,
    AdminCostsMetricsResponse,
    AdminExpensiveMailRow,
    AdminTokensMetricsResponse,
)
from backend.api.schemas.costs import CostSeriesPoint
from backend.api.services.admin_overview_support import langfuse_session_url, period
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings


def admin_costs_metrics(
    ctx: AppContext,
    settings: Settings,
    *,
    days: int = 30,
) -> AdminCostsMetricsResponse:
    start, end = period(days)
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

    unassigned = ctx.metrics_repo.sum_unassigned_cost_between(start, end)

    return AdminCostsMetricsResponse(
        days=days,
        series=series,
        total_usd=round(float(platform.get("cost_usd", 0.0)), 4),
        unassigned_cost_usd=round(unassigned, 4),
        by_account=by_account,
        top_mails=top_mails,
    )


def admin_tokens_metrics(
    ctx: AppContext, *, days: int = 30
) -> AdminTokensMetricsResponse:
    start, end = period(days)
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

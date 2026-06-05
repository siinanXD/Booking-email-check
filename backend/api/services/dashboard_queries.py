"""Dashboard KPI queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.ai.domain.booking.booking_mail_counts import aggregate_booking_mail_stats
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.api.schemas.costs import CostSeriesPoint, CostsResponse
from backend.api.schemas.dashboard import DashboardStats
from backend.core.config.factory import AppContext
from backend.core.models.email import ProcessingState
from backend.infrastructure.repositories.tenant_scope import with_account_filter


def dashboard_stats(ctx: AppContext, account_id: str) -> DashboardStats:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    today_iso = today_start.isoformat()
    week_iso = week_start.isoformat()

    email_repo = ctx.email_repo
    metrics_repo = ctx.metrics_repo

    total_today = email_repo.count_received_since(today_iso, account_id=account_id)
    total_week = email_repo.count_received_since(week_iso, account_id=account_id)
    processed_today = email_repo.count_by_state_since(
        ProcessingState.APPROVED,
        today_iso,
        account_id=account_id,
    )
    spam_today = email_repo.count_by_state_since(
        ProcessingState.DISCARDED,
        today_iso,
        account_id=account_id,
    )
    cost_today = metrics_repo.sum_cost_between(today_start, now, account_id=account_id)
    cost_week = metrics_repo.sum_cost_between(week_start, now, account_id=account_id)
    mail_count_week = metrics_repo.count_between(week_start, now, account_id=account_id)
    avg_cost = cost_week / mail_count_week if mail_count_week else 0.0

    grounding_today = count_grounding_since(ctx, account_id, today_iso)
    pending_grounding = ctx.review_repo.count_open_grounding(account_id=account_id)
    booking_stats = aggregate_booking_mail_stats(
        email_repo,
        ctx.extraction_repo,
        account_id=account_id,
        today_iso=today_iso,
        week_iso=week_iso,
    )
    nav_completed = ctx.review_repo.count_by_status_since(
        ["completed"],
        week_iso,
        account_id=account_id,
    )
    pending_booking = count_pending_booking_reviews(ctx, account_id)
    reviewed_today = ctx.review_repo.count_by_status_since(
        ["approved", "rejected"],
        today_iso,
        account_id=account_id,
    )
    last_email_received_at = email_repo.max_received_at(account_id=account_id)
    last_booking_detected_at = (
        booking_stats.latest_booking_received_at.isoformat()
        if booking_stats.latest_booking_received_at is not None
        else None
    )
    mail_conn = ctx.mail_connection_repo.get(account_id)
    last_sync_at = (
        mail_conn.last_sync_at.isoformat()
        if mail_conn and mail_conn.last_sync_at
        else None
    )

    return DashboardStats(
        total_emails_today=total_today,
        total_emails_week=total_week,
        pending_review=pending_booking,
        processed_today=processed_today,
        spam_discarded_today=spam_today,
        new_bookings_today=booking_stats.intents_today.get(
            BookingIntent.NEW_BOOKING.value, 0
        ),
        cancellations_today=booking_stats.intents_today.get(
            BookingIntent.CANCELLATION.value, 0
        ),
        changes_today=booking_stats.intents_today.get(BookingIntent.CHANGE.value, 0),
        booking_emails_total=booking_stats.booking_total,
        booking_emails_week=booking_stats.booking_week,
        cost_today_usd=round(cost_today, 4),
        cost_week_usd=round(cost_week, 4),
        avg_cost_per_mail_usd=round(avg_cost, 4),
        grounding_failures_today=grounding_today,
        pending_grounding_review=pending_grounding,
        reviewed_today=reviewed_today,
        last_sync_at=last_sync_at,
        last_email_received_at=last_email_received_at,
        last_booking_detected_at=last_booking_detected_at,
        mail_fetch_unread_only=ctx.settings.outlook_fetch_unread_only,
        nav_bookings=booking_stats.intents_all.get(BookingIntent.NEW_BOOKING.value, 0),
        nav_cancellations=booking_stats.intents_all.get(
            BookingIntent.CANCELLATION.value, 0
        ),
        nav_changes=booking_stats.intents_all.get(BookingIntent.CHANGE.value, 0),
        nav_messages=(
            booking_stats.intents_all.get(BookingIntent.GUEST_INQUIRY.value, 0)
            + booking_stats.intents_all.get(BookingIntent.COMPLAINT.value, 0)
        ),
        nav_ground_zero=nav_ground_zero(ctx, account_id),
        nav_completed=nav_completed,
    )


def demo_stats() -> DashboardStats:
    return DashboardStats(
        total_emails_today=12,
        total_emails_week=48,
        pending_review=2,
        processed_today=10,
        spam_discarded_today=1,
        new_bookings_today=5,
        cancellations_today=1,
        changes_today=2,
        booking_emails_total=12,
        booking_emails_week=12,
        cost_today_usd=0.42,
        cost_week_usd=2.1,
        avg_cost_per_mail_usd=0.044,
        grounding_failures_today=0,
        pending_grounding_review=0,
        reviewed_today=8,
        last_sync_at="2026-06-03T10:00:00+00:00",
        last_email_received_at="2026-06-03T09:45:00+00:00",
        last_booking_detected_at="2026-06-03T09:30:00+00:00",
        mail_fetch_unread_only=False,
    )


def costs(
    ctx: AppContext,
    account_id: str | None,
    *,
    from_date: str | None,
    to_date: str | None,
    group_by: str,
) -> CostsResponse:
    end = datetime.now(UTC)
    if to_date:
        end = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
    start = end - timedelta(days=30)
    if from_date:
        start = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
    if group_by != "day":
        pass
    series_raw = ctx.metrics_repo.aggregate_by_day(start, end, account_id=account_id)
    series = [CostSeriesPoint.model_validate(row) for row in series_raw]
    total = sum(p.cost_usd for p in series)
    return CostsResponse(series=series, total_usd=round(total, 4))


def count_grounding_since(ctx: AppContext, account_id: str, since_iso: str) -> int:
    """Neue Grounding-Fälle heute (nur noch ausstehend — nach Freigabe Flag weg)."""
    col = ctx.review_repo._col
    query = with_account_filter(
        {
            "grounding_flag": True,
            "review_status": "pending",
            "updated_at": {"$gte": since_iso},
        },
        account_id,
    )
    return int(col.count_documents(query))


def count_pending_booking_reviews(ctx: AppContext, account_id: str) -> int:
    from backend.api.services.review_queue_service import count_eligible_pending_reviews

    return count_eligible_pending_reviews(ctx, account_id)


def nav_ground_zero(ctx: AppContext, account_id: str) -> int:
    """Offene Grounding-Fälle für Sidebar-Badge."""
    return ctx.review_repo.count_open_grounding(account_id=account_id)

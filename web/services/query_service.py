"""Lesezugriffe für Dashboard und Listen."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

from config.factory import AppContext
from models.email import ProcessingState
from schemas.booking.taxonomy import BookingIntent
from web.schemas.costs import CostSeriesPoint, CostsResponse
from web.schemas.dashboard import DashboardStats
from web.schemas.emails import EmailDetail, EmailListItem, EmailListResponse


class QueryService:
    """Aggregationen und Mapping für die Web-API."""

    def __init__(self, ctx: AppContext) -> None:
        """Initialize the instance with its dependencies."""
        self._ctx = ctx

    def dashboard_stats(self) -> DashboardStats:
        """Berechnet Dashboard-KPIs aus Mongo."""
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        today_iso = today_start.isoformat()
        week_iso = week_start.isoformat()

        email_repo = self._ctx.email_repo
        review_repo = self._ctx.review_repo
        metrics_repo = self._ctx.metrics_repo

        total_today = email_repo.count_updated_since(today_iso)
        total_week = email_repo.count_updated_since(week_iso)
        pending = review_repo.count_pending()
        processed_today = email_repo.count_by_state_since(
            ProcessingState.APPROVED,
            today_iso,
        )
        spam_today = email_repo.count_by_state_since(
            ProcessingState.DISCARDED,
            today_iso,
        )
        cost_today = metrics_repo.sum_cost_between(today_start, now)
        cost_week = metrics_repo.sum_cost_between(week_start, now)
        mail_count_week = metrics_repo.count_between(week_start, now)
        avg_cost = cost_week / mail_count_week if mail_count_week else 0.0

        grounding_today = self._count_grounding_since(today_iso)
        intents_today = self._intent_counts_since(today_iso)

        return DashboardStats(
            total_emails_today=total_today,
            total_emails_week=total_week,
            pending_review=pending,
            processed_today=processed_today,
            spam_discarded_today=spam_today,
            new_bookings_today=intents_today.get(BookingIntent.NEW_BOOKING.value, 0),
            cancellations_today=intents_today.get(
                BookingIntent.CANCELLATION.value,
                0,
            ),
            changes_today=intents_today.get(BookingIntent.CHANGE.value, 0),
            cost_today_usd=round(cost_today, 4),
            cost_week_usd=round(cost_week, 4),
            avg_cost_per_mail_usd=round(avg_cost, 4),
            grounding_failures_today=grounding_today,
        )

    def demo_stats(self) -> DashboardStats:
        """Statische Demo-Daten für leere Dev-DB."""
        return DashboardStats(
            total_emails_today=12,
            total_emails_week=48,
            pending_review=2,
            processed_today=10,
            spam_discarded_today=1,
            new_bookings_today=5,
            cancellations_today=1,
            changes_today=2,
            cost_today_usd=0.42,
            cost_week_usd=2.1,
            avg_cost_per_mail_usd=0.044,
            grounding_failures_today=0,
        )

    def list_emails(
        self,
        *,
        status: str | None,
        intent: str | None,
        platform: str | None,
        search: str | None,
        page: int,
        limit: int,
    ) -> EmailListResponse:
        """Paginierte E-Mail-Liste."""
        emails, total = self._ctx.email_repo.list_filtered(
            status=status,
            intent=intent,
            platform=platform,
            search=search,
            page=page,
            limit=limit,
        )
        items: list[EmailListItem] = []
        for email in emails:
            ext = self._ctx.extraction_repo.get_by_correlation_id(email.correlation_id)
            review = self._ctx.review_repo.get(email.correlation_id)
            intent_val = ext.intent.value if ext and ext.intent else None
            items.append(
                EmailListItem(
                    correlation_id=email.correlation_id,
                    message_id=email.message_id,
                    subject=email.subject,
                    from_address=email.from_address,
                    received_at=(
                        email.received_at.isoformat() if email.received_at else None
                    ),
                    platform=email.platform or (ext.platform if ext else None),
                    intent=intent_val,
                    booking_number=ext.booking_number if ext else None,
                    processing_state=email.processing_state.value,
                    review_status=review.review_status if review else None,
                    grounding_flag=review.grounding_flag if review else False,
                )
            )
        pages = ceil(total / limit) if limit else 0
        return EmailListResponse(
            items=items,
            total=total,
            page=page,
            pages=pages,
        )

    def get_email_detail(self, correlation_id: str) -> EmailDetail | None:
        """Vollständiges Mail-Detail."""
        email = self._ctx.email_repo.get_by_correlation_id(correlation_id)
        if email is None:
            return None
        ext = self._ctx.extraction_repo.get_by_correlation_id(correlation_id)
        review = self._ctx.review_repo.get(correlation_id)
        extraction_json: dict[str, Any] | None = None
        if ext is not None:
            extraction_json = ext.model_dump(mode="json")
        return EmailDetail(
            correlation_id=email.correlation_id,
            message_id=email.message_id,
            subject=email.subject,
            from_address=email.from_address,
            to_addresses=email.to_addresses,
            body_text=email.body_text,
            received_at=email.received_at.isoformat() if email.received_at else None,
            platform=email.platform,
            intent=ext.intent.value if ext and ext.intent else None,
            booking_number=ext.booking_number if ext else None,
            processing_state=email.processing_state.value,
            review_status=review.review_status if review else None,
            grounding_flag=review.grounding_flag if review else False,
            draft_body=review.draft_body if review else "",
            extraction=extraction_json,
            approved_body=review.approved_body if review else None,
        )

    def costs(
        self,
        *,
        from_date: str | None,
        to_date: str | None,
        group_by: str,
    ) -> CostsResponse:
        """Kosten-Zeitreihe."""
        end = datetime.now(UTC)
        if to_date:
            end = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        start = end - timedelta(days=30)
        if from_date:
            start = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        if group_by != "day":
            pass
        series_raw = self._ctx.metrics_repo.aggregate_by_day(start, end)
        series = [CostSeriesPoint.model_validate(row) for row in series_raw]
        total = sum(p.cost_usd for p in series)
        return CostsResponse(series=series, total_usd=round(total, 4))

    def _count_grounding_since(self, since_iso: str) -> int:
        col = self._ctx.review_repo._col
        return int(
            col.count_documents(
                {
                    "grounding_flag": True,
                    "updated_at": {"$gte": since_iso},
                }
            )
        )

    def _intent_counts_since(self, since_iso: str) -> dict[str, int]:
        pipeline: Sequence[Mapping[str, Any]] = [
            {"$match": {"updated_at": {"$gte": since_iso}}},
            {
                "$group": {
                    "_id": "$extraction.intent",
                    "count": {"$sum": 1},
                }
            },
        ]
        col = self._ctx.extraction_repo._col
        result: dict[str, int] = {}
        for row in col.aggregate(pipeline):
            key = row.get("_id")
            if key:
                result[str(key)] = int(row.get("count", 0))
        return result

"""Lesezugriffe für Dashboard und Listen."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

from config.factory import AppContext
from models.email import ProcessingState, StoredEmail
from schemas.booking.taxonomy import BookingIntent
from services.booking_relevance import classify_booking_mail, count_booking_mails
from web.schemas.costs import CostSeriesPoint, CostsResponse
from web.schemas.dashboard import DashboardStats
from web.schemas.emails import EmailDetail, EmailListItem, EmailListResponse
from web.schemas.review import ReviewQueueItem


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
        metrics_repo = self._ctx.metrics_repo

        total_today = email_repo.count_received_since(today_iso)
        total_week = email_repo.count_received_since(week_iso)
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
        _, booking_week, _ = count_booking_mails(
            email_repo,
            self._ctx.extraction_repo,
            since_iso=week_iso,
        )
        _, booking_total, _ = count_booking_mails(
            email_repo,
            self._ctx.extraction_repo,
        )
        _, _, intents_today = count_booking_mails(
            email_repo,
            self._ctx.extraction_repo,
            since_iso=today_iso,
        )
        pending_booking = self._count_pending_booking_reviews()

        return DashboardStats(
            total_emails_today=total_today,
            total_emails_week=total_week,
            pending_review=pending_booking,
            processed_today=processed_today,
            spam_discarded_today=spam_today,
            new_bookings_today=intents_today.get(BookingIntent.NEW_BOOKING.value, 0),
            cancellations_today=intents_today.get(
                BookingIntent.CANCELLATION.value,
                0,
            ),
            changes_today=intents_today.get(BookingIntent.CHANGE.value, 0),
            booking_emails_total=booking_total,
            booking_emails_week=booking_week,
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
            booking_emails_total=12,
            booking_emails_week=12,
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
        intents: list[str] | None,
        platform: str | None,
        search: str | None,
        booking_related: bool,
        page: int,
        limit: int,
    ) -> EmailListResponse:
        """Paginierte E-Mail-Liste."""
        fetch_limit = 500 if booking_related else limit
        fetch_page = 1 if booking_related else page
        emails, total = self._ctx.email_repo.list_filtered(
            status=status,
            intent=intent,
            intents=intents,
            platform=platform,
            search=search,
            booking_related=booking_related,
            page=fetch_page,
            limit=fetch_limit,
        )
        if booking_related:
            strict: list[StoredEmail] = []
            for email in emails:
                ext = self._ctx.extraction_repo.get_by_correlation_id(
                    email.correlation_id
                )
                if classify_booking_mail(email, ext).is_booking:
                    strict.append(email)
            total = len(strict)
            offset = max(page - 1, 0) * limit
            emails = strict[offset : offset + limit]
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

    def list_review_pending(self, *, limit: int = 50) -> list[ReviewQueueItem]:
        """Review-Warteschlange — nur echte Buchungs-Mails."""
        items: list[ReviewQueueItem] = []
        for record in self._ctx.review_repo.list_pending(limit=200):
            email = self._ctx.email_repo.get_by_correlation_id(record.correlation_id)
            if email is None:
                continue
            ext = self._ctx.extraction_repo.get_by_correlation_id(record.correlation_id)
            if not classify_booking_mail(email, ext).is_booking:
                continue
            items.append(
                ReviewQueueItem(
                    correlation_id=record.correlation_id,
                    message_id=record.message_id,
                    subject=email.subject,
                    from_address=email.from_address,
                    intent=record.intent,
                    draft_body=record.draft_body,
                    grounding_flag=record.grounding_flag,
                    review_status=record.review_status,
                    received_at=(
                        email.received_at.isoformat() if email.received_at else None
                    ),
                )
            )
            if len(items) >= limit:
                break
        return items

    def _count_pending_booking_reviews(self) -> int:
        return len(self.list_review_pending(limit=500))

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
        from services.booking_relevance import mongo_noise_exclusion

        received_match: dict[str, Any] = {"received_at": {"$gte": since_iso}}
        noise = mongo_noise_exclusion()
        if noise:
            received_match = {"$and": [received_match, noise]}
        pipeline: Sequence[Mapping[str, Any]] = [
            {"$match": received_match},
            {
                "$lookup": {
                    "from": "extractions",
                    "localField": "correlation_id",
                    "foreignField": "_id",
                    "as": "ext",
                }
            },
            {"$unwind": {"path": "$ext", "preserveNullAndEmptyArrays": False}},
            {
                "$group": {
                    "_id": "$ext.extraction.intent",
                    "count": {"$sum": 1},
                }
            },
        ]
        col = self._ctx.email_repo._col
        result: dict[str, int] = {}
        for row in col.aggregate(pipeline):
            key = row.get("_id")
            if key:
                result[str(key)] = int(row.get("count", 0))
        return result

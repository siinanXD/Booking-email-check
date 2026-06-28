"""Email list and review queue queries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from math import ceil
from typing import Any

from backend.ai.domain.booking.booking_relevance import effective_booking_intent
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services.mail_summary import MailSummaryService
from backend.api.schemas.emails import EmailDetail, EmailListItem, EmailListResponse
from backend.api.schemas.review import ReviewQueueItem
from backend.api.services.date_range import parse_date_range
from backend.core.config.factory import AppContext
from backend.core.models.email import StoredEmail
from backend.core.utils.language import detect_reply_language
from backend.infrastructure.repositories.review_repository import ReviewRecord


class _EmailListContext:
    """Batch-geladene Extraktionen und Reviews für Listen-Queries."""

    __slots__ = ("extractions", "reviews")

    def __init__(
        self,
        extractions: dict[str, BookingExtraction],
        reviews: dict[str, ReviewRecord],
    ) -> None:
        self.extractions = extractions
        self.reviews = reviews


def _batch_email_list_context(
    ctx: AppContext,
    account_id: str,
    correlation_ids: list[str],
) -> _EmailListContext:
    return _EmailListContext(
        extractions=ctx.extraction_repo.map_by_correlation_ids(
            correlation_ids,
            account_id=account_id,
        ),
        reviews=ctx.review_repo.map_by_correlation_ids(
            correlation_ids,
            account_id=account_id,
        ),
    )


def _email_to_list_item(
    email: StoredEmail,
    batch: _EmailListContext,
) -> EmailListItem:
    ext = batch.extractions.get(email.correlation_id)
    review = batch.reviews.get(email.correlation_id)
    intent_val = effective_booking_intent(email, ext)
    intent_str = intent_val.value if intent_val else None
    return EmailListItem(
        correlation_id=email.correlation_id,
        message_id=email.message_id,
        subject=email.subject,
        from_address=email.from_address,
        received_at=email.received_at.isoformat() if email.received_at else None,
        platform=email.platform or (ext.platform if ext else None),
        intent=intent_str,
        booking_number=ext.booking_number if ext else None,
        processing_state=email.processing_state.value,
        review_status=review.review_status if review else None,
        grounding_flag=review.grounding_flag if review else False,
    )


def list_emails(
    ctx: AppContext,
    account_id: str,
    *,
    status: str | None,
    intent: str | None,
    intents: list[str] | None,
    platform: str | None,
    search: str | None,
    booking_related: bool,
    workflow_slug: str | None,
    page: int,
    limit: int,
    from_date: str | None = None,
    to_date: str | None = None,
) -> EmailListResponse:
    since_iso: str | None = None
    until_iso: str | None = None
    if from_date or to_date:
        since_iso, until_iso = parse_date_range(
            from_date=from_date,
            to_date=to_date,
        )
    if workflow_slug:
        return _list_emails_for_workflow(
            ctx,
            account_id,
            workflow_slug=workflow_slug.strip(),
            search=search,
            page=page,
            limit=limit,
        )
    # Booking-Kategorien filtern/paginieren jetzt DB-seitig über die
    # vorberechneten Felder is_booking/effective_intent (siehe list_filtered).
    emails, total = ctx.email_repo.list_filtered(
        account_id=account_id,
        status=status,
        intent=intent,
        intents=intents,
        platform=platform,
        search=search,
        booking_related=booking_related,
        page=page,
        limit=limit,
        received_since=since_iso,
        received_until=until_iso,
    )
    page_batch = _batch_email_list_context(
        ctx,
        account_id,
        [email.correlation_id for email in emails],
    )
    items = [_email_to_list_item(email, page_batch) for email in emails]
    pages = ceil(total / limit) if limit else 0
    return EmailListResponse(items=items, total=total, page=page, pages=pages)


def _list_emails_for_workflow(
    ctx: AppContext,
    account_id: str,
    *,
    workflow_slug: str,
    search: str | None,
    page: int,
    limit: int,
) -> EmailListResponse:
    correlation_ids = ctx.extraction_repo.list_correlation_ids_by_workflow_slug(
        workflow_slug,
        account_id=account_id,
    )
    if not correlation_ids:
        return EmailListResponse(items=[], total=0, page=page, pages=0)
    emails = ctx.email_repo.list_by_correlation_ids(
        correlation_ids,
        account_id=account_id,
    )
    if search:
        needle = search.lower()
        emails = [
            e
            for e in emails
            if needle in e.subject.lower()
            or needle in e.from_address.lower()
            or needle in e.correlation_id.lower()
        ]
    matched = emails
    matched.sort(
        key=lambda e: e.received_at.timestamp() if e.received_at else 0,
        reverse=True,
    )
    total = len(matched)
    offset = max(page - 1, 0) * limit
    page_emails = matched[offset : offset + limit]
    page_batch = _batch_email_list_context(
        ctx,
        account_id,
        [email.correlation_id for email in page_emails],
    )
    items = [_email_to_list_item(email, page_batch) for email in page_emails]
    pages = ceil(total / limit) if limit else 0
    return EmailListResponse(items=items, total=total, page=page, pages=pages)


def get_email_detail(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
) -> EmailDetail | None:
    # Die vier Lookups hängen nicht voneinander ab – auf einem entfernten
    # Atlas-Cluster dominiert sonst die Round-Trip-Latenz (4× sequenziell).
    with ThreadPoolExecutor(max_workers=4) as pool:
        email_fut = pool.submit(
            ctx.email_repo.get_by_correlation_id,
            correlation_id,
            account_id=account_id,
        )
        ext_fut = pool.submit(
            ctx.extraction_repo.get_by_correlation_id,
            correlation_id,
            account_id=account_id,
        )
        review_fut = pool.submit(
            ctx.review_repo.get,
            correlation_id,
            account_id=account_id,
        )
        cached_summary_fut = pool.submit(
            ctx.mail_summary_repo.get,
            correlation_id,
            account_id=account_id,
        )
        email = email_fut.result()
        ext = ext_fut.result()
        review = review_fut.result()
        cached_summary = cached_summary_fut.result()

    if email is None:
        return None
    extraction_json: dict[str, Any] | None = None
    if ext is not None:
        extraction_json = ext.model_dump(mode="json")
    summary_svc = MailSummaryService(ctx.mail_summary_repo)
    summary = summary_svc.from_cache_or_build(
        email,
        ext,
        cached=cached_summary,
    )
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
        mail_summary=summary.summary_text,
        mail_sentiment=summary.sentiment,
        confidence=review.confidence if review else None,
        signals=list(review.signals) if review else [],
        grounding_span=review.grounding_span if review else None,
        escalated=review.escalated if review else False,
        auto_approved=review.auto_approved if review else False,
        reply_language=detect_reply_language(email.body_text),
    )


def list_review_pending(
    ctx: AppContext,
    account_id: str,
    *,
    limit: int = 50,
) -> list[ReviewQueueItem]:
    from backend.api.services.review_queue_service import list_review_queue

    return list_review_queue(ctx, account_id, queue="pending", limit=limit)

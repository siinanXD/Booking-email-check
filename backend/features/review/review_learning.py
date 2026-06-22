"""Lernen aus freigegebenen Reviews (Few-Shots + Vektorindex)."""

from __future__ import annotations

from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.config.factory import AppContext


def learn_from_approved_review(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
    approved_body: str | None,
) -> None:
    """Nach Freigabe: Beispiel speichern und Mail-Kontext neu indexieren."""
    email = ctx.email_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if email is None:
        return
    ext = ctx.extraction_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    review = ctx.review_repo.get(correlation_id, account_id=account_id)
    intent_val = (
        ext.intent.value
        if ext and ext.intent and ext.intent != BookingIntent.OTHER
        else (review.intent if review else None)
    )
    if not intent_val:
        intent_val = BookingIntent.NEW_BOOKING.value

    body_snippet = (email.body_text or "").strip()
    if body_snippet:
        ctx.tenant_learned_examples_repo.add_classify_example(
            account_id,
            subject=email.subject or "",
            body=body_snippet,
            intent=intent_val,
            correlation_id=correlation_id,
        )

    if ctx.indexing_service is not None and body_snippet:
        index_text = body_snippet
        final_body = (
            approved_body or (review.approved_body if review else None) or ""
        ).strip()
        if final_body:
            index_text = f"{index_text}\n\n--- Freigegebene Antwort ---\n{final_body}"
        ctx.indexing_service.schedule_index(
            correlation_id,
            index_text,
            ext,
            account_id=account_id,
            subject=email.subject,
        )

"""Review-Aktionen: abschließen, WhatsApp-Vorschau, Auto-Freigabe-Undo."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.domain.booking.extraction import (
    BookingExtraction,
)
from backend.api.schemas.review_whatsapp import WhatsAppPreviewResponse
from backend.core.config.factory import AppContext
from backend.core.models.email import ProcessingState
from backend.features.notifications.notification_preview import build_whatsapp_preview

# Zeitfenster (Sekunden), in dem eine Auto-Freigabe rückgängig gemacht werden kann.
UNDO_WINDOW_SECONDS = 30


def undo_auto_approval(
    ctx: AppContext, account_id: str, correlation_id: str
) -> str | None:
    """Macht eine Auto-Freigabe rückgängig. Gibt Fehlertext zurück oder None (ok)."""
    record = ctx.review_repo.get(correlation_id, account_id=account_id)
    if record is None or not record.auto_approved or not record.auto_approved_at:
        return "Keine Auto-Freigabe zum Rückgängigmachen."
    try:
        approved_at = datetime.fromisoformat(record.auto_approved_at)
    except ValueError:
        return "Ungültiger Zeitstempel."
    if (datetime.now(UTC) - approved_at).total_seconds() > UNDO_WINDOW_SECONDS:
        return "Undo-Fenster abgelaufen."
    ctx.review_repo.update_status(
        correlation_id,
        "pending",
        account_id=account_id,
        extra_fields={"auto_approved": False},
    )
    ctx.email_repo.update_processing_state(
        record.message_id, ProcessingState.PENDING_REVIEW, account_id=account_id
    )
    return None


def complete_review(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
) -> dict[str, str]:
    """Markiert freigegebenen Review als abgeschlossen."""
    record = ctx.review_repo.get(correlation_id, account_id=account_id)
    if record is None:
        raise ValueError("Review not found")
    if record.review_status != "approved":
        raise ValueError("Only approved reviews can be completed")
    updated = ctx.review_repo.update_status(
        correlation_id,
        "completed",
        account_id=account_id,
    )
    if updated is None:
        raise ValueError("Review update failed")
    email = ctx.email_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if email is not None:
        ctx.email_repo.update_processing_state(
            email.message_id,
            ProcessingState.APPROVED,
            account_id=account_id,
        )
    return {"status": "completed", "correlation_id": correlation_id}


def whatsapp_preview(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
) -> WhatsAppPreviewResponse:
    """Template-Vorschau für Review-Freigabe."""
    ext = ctx.extraction_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if ext is None:
        ext = BookingExtraction()
    return build_whatsapp_preview(
        ctx,
        account_id,
        correlation_id,
        ext,
    )

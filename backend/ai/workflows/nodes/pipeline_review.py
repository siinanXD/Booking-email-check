"""Human review and finalize nodes for the email workflow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.ai.domain.booking.source_consistency import detect_source_conflicts
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import ProcessingState
from backend.core.models.response import ReviewStatus
from backend.features.review.auto_approve import should_auto_approve

if TYPE_CHECKING:
    from backend.features.cleaning.service import CleaningScheduleService
    from backend.features.notifications.notification_service import (
        NotificationService,
    )
    from backend.infrastructure.observability.langfuse_client import LangfuseTracer
    from backend.infrastructure.observability.review_feedback import (
        ReviewFeedbackTracker,
    )
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.platform_settings_repository import (
        PlatformSettingsRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository

logger = logging.getLogger(__name__)

# Unter dieser Grounding-Konfidenz wird priorisiert an einen Menschen eskaliert.
_ESCALATE_FLOOR = 0.5


def _intent_str(intent_val: object | None) -> str | None:
    if intent_val is None:
        return None
    return intent_val.value if hasattr(intent_val, "value") else str(intent_val)


class PipelineReviewMixin:
    """Review gate and post-approval finalization."""

    _email_repo: EmailRepository
    _review_repo: ReviewRepository | None
    _notification_service: NotificationService | None
    _cleaning_service: CleaningScheduleService | None
    _feedback_tracker: ReviewFeedbackTracker | None
    _langfuse_tracer: LangfuseTracer | None
    _platform_settings_repo: PlatformSettingsRepository | None

    def _decide_auto_approve(
        self, account_id: str | None, intent: str | None, confidence: float
    ) -> bool:
        """Auto-Freigabe nur bei aktiviertem, passendem Mandanten-Setting."""
        repo = self._platform_settings_repo
        if repo is None or not account_id:
            return False
        settings = repo.get(account_id)
        if settings is None:
            return False
        return should_auto_approve(confidence, intent, settings.auto_approve)

    @staticmethod
    def _should_escalate(intent: str | None, confidence: float) -> bool:
        """Beschwerden und niedrige Konfidenz priorisiert an einen Menschen."""
        if intent == "complaint":
            return True
        return confidence < _ESCALATE_FLOOR

    def human_review(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        review = state.get("review") or ReviewStatus(
            correlation_id=email.correlation_id,
            status="pending",
        )
        draft = state.get("draft")
        intent = _intent_str(state.get("intent"))
        auto_approve = False
        if review.status == "pending":
            confidence = draft.confidence if draft is not None else 1.0
            extraction = state.get("extraction")
            conflicts = (
                detect_source_conflicts(email, extraction)
                if extraction is not None
                else []
            )
            source_flags = [c.message for c in conflicts]
            source_escalate = any(c.escalate for c in conflicts)
            # Widersprüchliche Quelle nie automatisch versenden.
            auto_approve = not source_escalate and self._decide_auto_approve(
                email.account_id, intent, confidence
            )
            escalated = not auto_approve and (
                self._should_escalate(intent, confidence) or source_escalate
            )
            review.escalated = escalated
            if self._review_repo is not None:
                self._review_repo.upsert_pending(
                    correlation_id=email.correlation_id,
                    message_id=email.message_id,
                    draft_body=draft.body if draft is not None else "",
                    grounding_flag=bool(state.get("grounding_flag")),
                    intent=intent,
                    account_id=email.account_id,
                    confidence=confidence,
                    signals=draft.grounding_signals if draft is not None else [],
                    grounding_span=draft.grounding_span if draft is not None else None,
                    escalated=escalated,
                    source_flags=source_flags,
                )
        if review.status == "approved":
            proc = ProcessingState.APPROVED
        elif review.status == "rejected":
            proc = ProcessingState.REJECTED
        else:
            proc = ProcessingState.PENDING_REVIEW
        self._email_repo.update_processing_state(
            email.message_id, proc, account_id=email.account_id
        )
        result: EmailWorkflowState = {"review": review}
        if auto_approve:
            result["auto_approve"] = True
            result["auto_approve_body"] = draft.body if draft is not None else ""
        return result

    def finalize(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        review = state.get("review")
        status = review.status if review else "approved"
        if status == "approved":
            proc = ProcessingState.APPROVED
        elif status == "rejected":
            proc = ProcessingState.REJECTED
        else:
            proc = ProcessingState.PENDING_REVIEW
        self._email_repo.update_processing_state(
            email.message_id, proc, account_id=email.account_id
        )
        if status == "approved":
            extraction = state.get("extraction")
            if extraction is not None and self._notification_service is not None:
                self._notification_service.dispatch_after_approval(
                    email.correlation_id,
                    extraction,
                    account_id=email.account_id,
                )
            if extraction is not None and self._cleaning_service is not None:
                # Putzplan-Pflege darf den Mail-Workflow nie unterbrechen.
                try:
                    self._cleaning_service.process_booking_event(
                        email.correlation_id,
                        extraction,
                        account_id=email.account_id,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Putzplan-Verarbeitung fehlgeschlagen für %s",
                        email.correlation_id,
                    )
        approved_body = review.approved_body if review else None
        if self._feedback_tracker is not None and self._langfuse_tracer is not None:
            draft = state.get("draft")
            trace_id = draft.langfuse_trace_id if draft is not None else None
            if status == "approved" and approved_body:
                self._feedback_tracker.record(
                    email.correlation_id,
                    draft.body if draft is not None else "",
                    approved_body,
                    self._langfuse_tracer,
                    trace_id=trace_id,
                )
            elif status == "rejected":
                self._feedback_tracker.record_rejection(
                    email.correlation_id,
                    self._langfuse_tracer,
                    trace_id=trace_id,
                    reason=review.reviewer_note if review else None,
                )
        return {
            "review": ReviewStatus(
                correlation_id=email.correlation_id,
                status=status,
                approved_body=review.approved_body if review else None,
            ),
        }

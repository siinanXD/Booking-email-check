"""Human review and finalize nodes for the email workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import ProcessingState
from backend.core.models.response import ReviewStatus

if TYPE_CHECKING:
    from backend.features.notifications.notification_service import (
        NotificationService,
    )
    from backend.infrastructure.observability.langfuse_client import LangfuseTracer
    from backend.infrastructure.observability.review_feedback import (
        ReviewFeedbackTracker,
    )
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.review_repository import ReviewRepository


def _intent_str(intent_val: object | None) -> str | None:
    if intent_val is None:
        return None
    return intent_val.value if hasattr(intent_val, "value") else str(intent_val)


class PipelineReviewMixin:
    """Review gate and post-approval finalization."""

    _email_repo: EmailRepository
    _review_repo: ReviewRepository | None
    _notification_service: NotificationService | None
    _feedback_tracker: ReviewFeedbackTracker | None
    _langfuse_tracer: LangfuseTracer | None

    def human_review(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        review = state.get("review") or ReviewStatus(
            correlation_id=email.correlation_id,
            status="pending",
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
        if review.status == "pending" and self._review_repo is not None:
            draft = state.get("draft")
            draft_body = draft.body if draft is not None else ""
            self._review_repo.upsert_pending(
                correlation_id=email.correlation_id,
                message_id=email.message_id,
                draft_body=draft_body,
                grounding_flag=bool(state.get("grounding_flag")),
                intent=_intent_str(state.get("intent")),
                account_id=email.account_id,
            )
        return {"review": review}

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
        if status == "approved" and self._notification_service is not None:
            extraction = state.get("extraction")
            if extraction is not None:
                self._notification_service.dispatch_after_approval(
                    email.correlation_id,
                    extraction,
                    account_id=email.account_id,
                )
        approved_body = review.approved_body if review else None
        if (
            status == "approved"
            and approved_body
            and self._feedback_tracker is not None
            and self._langfuse_tracer is not None
        ):
            draft = state.get("draft")
            draft_body = draft.body if draft is not None else ""
            self._feedback_tracker.record(
                email.correlation_id,
                draft_body,
                approved_body,
                self._langfuse_tracer,
            )
        return {
            "review": ReviewStatus(
                correlation_id=email.correlation_id,
                status=status,
                approved_body=review.approved_body if review else None,
            ),
        }

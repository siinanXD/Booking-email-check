"""LangGraph node implementations for the email workflow."""

from __future__ import annotations

from backend.ai.domain.booking.triage import TriageOutcome, TriageResult
from backend.ai.services.classification import ClassificationService
from backend.ai.services.extraction import ExtractionService
from backend.ai.services.indexing import IndexingService
from backend.ai.services.ingestion import IngestionService
from backend.ai.services.response_generation import ResponseGenerationService
from backend.ai.services.retrieval import RetrievalService
from backend.ai.services.validation import ValidationService
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import IncomingEmail, ProcessingState, StoredEmail
from backend.core.models.response import ReviewStatus
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository


def triage_from_email(email: StoredEmail) -> TriageResult:
    outcome = TriageOutcome.RELEVANT
    if email.triage_outcome:
        try:
            outcome = TriageOutcome(email.triage_outcome)
        except ValueError:
            outcome = TriageOutcome.UNKNOWN_DOMAIN
    return TriageResult(outcome=outcome, reason="ingested")


class WorkflowNodes:
    """Node callables bound to workflow services."""

    def __init__(
        self,
        *,
        ingestion: IngestionService,
        classification: ClassificationService,
        extraction: ExtractionService,
        validation: ValidationService,
        retrieval: RetrievalService,
        response_gen: ResponseGenerationService,
        email_repo: EmailRepository,
        extraction_repo: ExtractionRepository,
        indexing: IndexingService | None,
        alerts: AlertService | None,
        review_repo: ReviewRepository | None,
        notification_service: NotificationService | None,
        feedback_tracker: ReviewFeedbackTracker | None = None,
        langfuse_tracer: LangfuseTracer | None = None,
    ) -> None:
        self._ingestion = ingestion
        self._classification = classification
        self._extraction = extraction
        self._validation = validation
        self._retrieval = retrieval
        self._response_gen = response_gen
        self._email_repo = email_repo
        self._extraction_repo = extraction_repo
        self._indexing = indexing
        self._alerts = alerts
        self._review_repo = review_repo
        self._notification_service = notification_service
        self._feedback_tracker = feedback_tracker
        self._langfuse_tracer = langfuse_tracer

    def ingest(self, state: EmailWorkflowState) -> EmailWorkflowState:
        raw = state.get("email")
        if isinstance(raw, IncomingEmail):
            result = self._ingestion.ingest(raw)
        elif isinstance(raw, StoredEmail):
            return {
                "email": raw,
                "ingest_duplicate": True,
                "ingest_discarded": False,
                "triage": triage_from_email(raw),
            }
        else:
            msg = "email must be IncomingEmail or StoredEmail"
            raise TypeError(msg)
        email = result.email
        discarded = result.discarded or (
            email.triage_outcome == TriageOutcome.SPAM_PHISHING.value
        )
        return {
            "email": email,
            "ingest_duplicate": result.duplicate,
            "ingest_discarded": discarded,
            "triage": (
                triage_from_email(email)
                if not discarded
                else TriageResult(
                    outcome=TriageOutcome.SPAM_PHISHING,
                    reason=result.triage_reason or "spam",
                )
            ),
        }

    def classify(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        intent = self._classification.classify(email)
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.CLASSIFIED,
            account_id=email.account_id,
        )
        return {"intent": intent}

    def extract(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        intent = state.get("intent")
        extraction = self._extraction.extract(email, intent=intent)
        self._extraction_repo.save(
            email.correlation_id,
            email.message_id,
            extraction,
            account_id=email.account_id,
        )
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.EXTRACTED,
            account_id=email.account_id,
        )
        return {"extraction": extraction}

    def validate(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        extraction = state["extraction"]
        result = self._validation.validate(extraction)
        if result.valid:
            self._email_repo.update_processing_state(
                email.message_id,
                ProcessingState.VALIDATED,
                account_id=email.account_id,
            )
            if self._indexing is not None:
                self._indexing.schedule_index(
                    email.correlation_id,
                    email.body_text,
                    extraction,
                )
        return {"validation_errors": result.errors}

    def retrieve(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        extraction = state.get("extraction")
        hits = self._retrieval.retrieve(email, extraction, include_similar=True)
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.RETRIEVED,
            account_id=email.account_id,
        )
        return {"retrieval": hits}

    def draft(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        extraction = state["extraction"]
        hits = state.get("retrieval")
        draft = self._response_gen.generate_draft(email, extraction, hits)
        grounding_flag = not draft.grounding_ok
        if grounding_flag and self._alerts:
            self._alerts.check_grounding_suspect(email.correlation_id)
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.DRAFTED,
            account_id=email.account_id,
        )
        intent_str = _intent_str(state.get("intent"))
        if self._review_repo is not None:
            self._review_repo.upsert_pending(
                correlation_id=email.correlation_id,
                message_id=email.message_id,
                draft_body=draft.body,
                grounding_flag=grounding_flag,
                intent=intent_str,
                account_id=email.account_id,
            )
        return {"draft": draft, "grounding_flag": grounding_flag}

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


def _intent_str(intent_val: object | None) -> str | None:
    if intent_val is None:
        return None
    return intent_val.value if hasattr(intent_val, "value") else str(intent_val)

"""LangGraph node implementations for the email workflow."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.domain.booking.triage import TriageOutcome, TriageResult
from backend.ai.services.classification import ClassificationService
from backend.ai.services.extraction import ExtractionService
from backend.ai.services.indexing import IndexingService
from backend.ai.services.ingestion import IngestionService
from backend.ai.services.response_generation import ResponseGenerationService
from backend.ai.services.retrieval import RetrievalService
from backend.ai.services.tenant_workflow_runtime import (
    TenantWorkflowExecutor,
    WorkflowRouter,
)
from backend.ai.services.validation import ValidationService
from backend.ai.workflows.nodes.pipeline_review import PipelineReviewMixin
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import IncomingEmail, ProcessingState, StoredEmail
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository
from backend.infrastructure.repositories.tenant_workflow_repository import (
    TenantWorkflowRepository,
)


def triage_from_email(email: StoredEmail) -> TriageResult:
    outcome = TriageOutcome.RELEVANT
    if email.triage_outcome:
        try:
            outcome = TriageOutcome(email.triage_outcome)
        except ValueError:
            outcome = TriageOutcome.UNKNOWN_DOMAIN
    return TriageResult(outcome=outcome, reason="ingested")


class WorkflowNodes(PipelineReviewMixin):
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
        workflow_router: WorkflowRouter | None = None,
        tenant_workflow_executor: TenantWorkflowExecutor | None = None,
        tenant_workflow_repo: TenantWorkflowRepository | None = None,
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
        self._workflow_router = workflow_router
        self._tenant_executor = tenant_workflow_executor
        self._tenant_workflow_repo = tenant_workflow_repo

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
        if self._workflow_router is not None and self._tenant_executor is not None:
            routed = self._workflow_router.match(email.account_id, email)
            if routed is not None:
                workflow = routed.workflow
                if self._tenant_executor.classify_match(workflow, email):
                    self._email_repo.update_processing_state(
                        email.message_id,
                        ProcessingState.CLASSIFIED,
                        account_id=email.account_id,
                    )
                    return {
                        "workflow_id": workflow.id,
                        "workflow_slug": workflow.slug,
                        "intent": BookingIntent.OTHER,
                    }
        intent = self._classification.classify(email)
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.CLASSIFIED,
            account_id=email.account_id,
        )
        return {"intent": intent}

    def extract(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        workflow_id = state.get("workflow_id")
        if (
            workflow_id
            and self._tenant_workflow_repo is not None
            and self._tenant_executor is not None
        ):
            workflow = self._tenant_workflow_repo.get(
                email.account_id or "", workflow_id
            )
            if workflow is not None:
                custom = self._tenant_executor.extract_fields(workflow, email)
                extraction = BookingExtraction(
                    intent=BookingIntent.OTHER,
                    confidence=float(custom.get("confidence", 0.9) or 0.9),
                )
                self._extraction_repo.save(
                    email.correlation_id,
                    email.message_id,
                    extraction,
                    account_id=email.account_id,
                    workflow_id=workflow.id,
                    workflow_slug=workflow.slug,
                    custom_fields=custom,
                )
                self._email_repo.update_processing_state(
                    email.message_id,
                    ProcessingState.EXTRACTED,
                    account_id=email.account_id,
                )
                return {"extraction": extraction, "custom_extraction": custom}
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
        workflow_id = state.get("workflow_id")
        if (
            workflow_id
            and self._tenant_workflow_repo is not None
            and self._tenant_executor is not None
        ):
            workflow = self._tenant_workflow_repo.get(
                email.account_id or "", workflow_id
            )
            custom = state.get("custom_extraction") or {}
            if workflow is not None and isinstance(custom, dict):
                errors = self._tenant_executor.validate_fields(workflow, custom)
                if not errors:
                    self._email_repo.update_processing_state(
                        email.message_id,
                        ProcessingState.VALIDATED,
                        account_id=email.account_id,
                    )
                return {"validation_errors": errors}
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
                    account_id=email.account_id,
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


def _intent_str(intent_val: object | None) -> str | None:
    if intent_val is None:
        return None
    return intent_val.value if hasattr(intent_val, "value") else str(intent_val)

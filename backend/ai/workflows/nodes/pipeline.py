"""LangGraph node implementations for the email workflow."""

from __future__ import annotations

from backend.ai.domain.booking.booking_relevance import (
    is_booking_relevant,
    relevance_fields,
)
from backend.ai.domain.booking.extraction_enrichment import enrich_extraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.domain.booking.triage import TriageOutcome
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
from backend.ai.workflows.nodes.cleaning_hook import schedule_cleaning_on_detect
from backend.ai.workflows.nodes.pipeline_review import PipelineReviewMixin
from backend.ai.workflows.nodes.tenant import TenantWorkflowMixin
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import IncomingEmail, ProcessingState, StoredEmail
from backend.features.cleaning.service import CleaningScheduleService
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository
from backend.infrastructure.repositories.tenant_workflow_repository import (
    TenantWorkflowRepository,
)


class WorkflowNodes(PipelineReviewMixin, TenantWorkflowMixin):
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
        cleaning_service: CleaningScheduleService | None = None,
        feedback_tracker: ReviewFeedbackTracker | None = None,
        langfuse_tracer: LangfuseTracer | None = None,
        workflow_router: WorkflowRouter | None = None,
        tenant_workflow_executor: TenantWorkflowExecutor | None = None,
        tenant_workflow_repo: TenantWorkflowRepository | None = None,
        platform_settings_repo: PlatformSettingsRepository | None = None,
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
        self._cleaning_service = cleaning_service
        self._feedback_tracker = feedback_tracker
        self._langfuse_tracer = langfuse_tracer
        self._workflow_router = workflow_router
        self._tenant_executor = tenant_workflow_executor
        self._tenant_workflow_repo = tenant_workflow_repo
        self._platform_settings_repo = platform_settings_repo

    def ingest(self, state: EmailWorkflowState) -> EmailWorkflowState:
        raw = state.get("email")
        if isinstance(raw, IncomingEmail):
            result = self._ingestion.ingest(raw)
        elif isinstance(raw, StoredEmail):
            return {
                "email": raw,
                "ingest_duplicate": True,
                "ingest_discarded": False,
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
        intent = state.get("intent")
        db = self._email_repo._col.database
        hints: list[str] | None = None
        if email.account_id:
            from backend.features.booking.property_catalog import known_property_names

            hints = known_property_names(db, email.account_id) or None
        raw = self._extraction.extract(email, intent=intent, known_property_names=hints)
        extraction = enrich_extraction(email, raw, known_property_names=hints)
        if email.account_id:
            from backend.features.booking.entity_sync import (
                ensure_property_from_extraction,
            )

            ensure_property_from_extraction(db, email.account_id, email, extraction)
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
            **relevance_fields(email, extraction),
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
            # Nur buchungsrelevante Mails indexieren (intent=other wäre Rauschen).
            if self._indexing is not None and is_booking_relevant(email, extraction):
                self._indexing.schedule_index(
                    email.correlation_id,
                    email.body_text,
                    extraction,
                    account_id=email.account_id,
                    subject=email.subject,
                    body_html=email.body_html,
                )
            if self._notification_service is not None:
                self._notification_service.dispatch_on_detect_if_enabled(
                    email.correlation_id, extraction, account_id=email.account_id
                )
            schedule_cleaning_on_detect(self._cleaning_service, email, extraction)
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
        # Der Review-Datensatz wird im human_review-Node mit vollem Detail
        # (Konfidenz, Signale, Eskalation) gespeichert.
        return {"draft": draft, "grounding_flag": grounding_flag}

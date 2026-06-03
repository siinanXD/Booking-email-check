"""LangGraph-Workflow: Ingestion bis Human Review."""

from __future__ import annotations

from typing import Any, cast

from langfuse.decorators import langfuse_context, observe
from langgraph.graph import END, StateGraph

from backend.ai.services.classification import ClassificationService
from backend.ai.services.extraction import ExtractionService
from backend.ai.services.indexing import IndexingService
from backend.ai.services.ingestion import IngestionService
from backend.ai.services.response_generation import ResponseGenerationService
from backend.ai.services.retrieval import RetrievalService
from backend.ai.services.validation import ValidationService
from backend.ai.workflows.helpers import finalize_mail_cost
from backend.ai.workflows.nodes.pipeline import WorkflowNodes
from backend.ai.workflows.routing import after_ingest, after_validate
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.response import ReviewStatus
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.mail_cost import MailCostTracker
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository


class EmailWorkflow:
    """Orchestriert die MVP-Pipeline mit Human-in-the-Loop-Interrupt."""

    def __init__(
        self,
        ingestion: IngestionService,
        classification: ClassificationService,
        extraction: ExtractionService,
        validation: ValidationService,
        retrieval: RetrievalService,
        response_gen: ResponseGenerationService,
        email_repo: EmailRepository,
        extraction_repo: ExtractionRepository,
        indexing: IndexingService | None = None,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
        review_repo: ReviewRepository | None = None,
        notification_service: NotificationService | None = None,
        checkpointer: object | None = None,
        feedback_tracker: ReviewFeedbackTracker | None = None,
        langfuse_tracer: LangfuseTracer | None = None,
        *,
        tracing: bool = False,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._email_repo = email_repo
        self._review_repo = review_repo
        self._mail_cost = mail_cost
        self._tracing = tracing
        self._nodes = WorkflowNodes(
            ingestion=ingestion,
            classification=classification,
            extraction=extraction,
            validation=validation,
            retrieval=retrieval,
            response_gen=response_gen,
            email_repo=email_repo,
            extraction_repo=extraction_repo,
            indexing=indexing,
            alerts=alerts,
            review_repo=review_repo,
            notification_service=notification_service,
            feedback_tracker=feedback_tracker,
            langfuse_tracer=langfuse_tracer,
        )
        self._alerts = alerts
        self._graph = self._build()
        from langgraph.checkpoint.memory import MemorySaver

        self._checkpointer = checkpointer or MemorySaver()
        self._app = self._graph.compile(
            checkpointer=self._checkpointer,
            interrupt_after=["human_review"],
        )

    def _build(self) -> StateGraph:
        graph: StateGraph = StateGraph(EmailWorkflowState)
        graph.add_node("ingest", self._nodes.ingest)
        graph.add_node("classify", self._nodes.classify)
        graph.add_node("extract", self._nodes.extract)
        graph.add_node("validate", self._nodes.validate)
        graph.add_node("retrieve", self._nodes.retrieve)
        graph.add_node("draft_response", self._nodes.draft)
        graph.add_node("human_review", self._nodes.human_review)
        graph.add_node("finalize", self._nodes.finalize)

        graph.set_entry_point("ingest")
        graph.add_conditional_edges(
            "ingest",
            after_ingest,
            {"end": END, "classify": "classify"},
        )
        graph.add_edge("classify", "extract")
        graph.add_edge("extract", "validate")
        graph.add_conditional_edges(
            "validate",
            lambda state: after_validate(
                state,
                email_repo=self._email_repo,
                alerts=self._alerts,
            ),
            {"end": END, "retrieve": "retrieve"},
        )
        graph.add_edge("retrieve", "draft_response")
        graph.add_edge("draft_response", "human_review")
        graph.add_edge("human_review", "finalize")
        graph.add_edge("finalize", END)
        return graph

    def run(self, email_input: Any, thread_id: str) -> dict[str, Any]:
        """Startet Workflow; stoppt vor human_review wenn nicht discarded."""
        return cast(dict[str, Any], self._run_observed(email_input, thread_id))

    @observe(name="mail_processed", capture_input=False, capture_output=False)  # type: ignore[misc]
    def _run_observed(self, email_input: Any, thread_id: str) -> dict[str, Any]:
        if self._tracing:
            langfuse_context.update_current_trace(session_id=thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        initial: EmailWorkflowState = {"email": email_input}
        result_dict: dict[str, Any] | None = None
        try:
            result_dict = dict(self._app.invoke(initial, config=config))
            return result_dict
        finally:
            finalize_mail_cost(self._mail_cost, email_input, result_dict)

    def resume_after_approval(
        self,
        thread_id: str,
        approved_body: str | None = None,
    ) -> dict[str, Any]:
        """Setzt Workflow nach Freigabe fort (gleiche thread_id)."""
        return self._resume_review(
            thread_id,
            status="approved",
            approved_body=approved_body,
        )

    def resume_after_rejection(
        self,
        thread_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Markiert Review als abgelehnt und schließt den Workflow ab."""
        return self._resume_review(
            thread_id,
            status="rejected",
            reviewer_note=reason,
        )

    def reject_after_review(
        self,
        thread_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Alias für resume_after_rejection."""
        return self.resume_after_rejection(thread_id, reason=reason)

    def _resume_review(
        self,
        thread_id: str,
        *,
        status: str,
        approved_body: str | None = None,
        reviewer_note: str | None = None,
    ) -> dict[str, Any]:
        """Gemeinsame Resume-Logik für Freigabe und Ablehnung."""
        config = {"configurable": {"thread_id": thread_id}}
        review = ReviewStatus(
            correlation_id=thread_id,
            status=status,
            approved_body=approved_body,
            reviewer_note=reviewer_note,
        )
        self._app.update_state(config, {"review": review}, as_node="human_review")
        result_dict: dict[str, Any] | None = None
        try:
            result_dict = dict(self._app.invoke(None, config=config))
            if self._review_repo is not None:
                email = self._email_repo.get_by_correlation_id(thread_id)
                account_id = email.account_id if email else None
                self._review_repo.update_status(
                    thread_id,
                    status,
                    account_id=account_id,
                    approved_body=approved_body,
                    reviewer_note=reviewer_note,
                )
            return result_dict
        finally:
            if self._mail_cost is not None:
                email = self._email_repo.get_by_correlation_id(thread_id)
                self._mail_cost.finalize(
                    thread_id,
                    account_id=email.account_id if email else None,
                )

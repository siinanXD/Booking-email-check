"""LangGraph-Workflow: Ingestion bis Human Review."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from models.email import IncomingEmail, ProcessingState, StoredEmail
from models.response import ReviewStatus
from observability.alerts import AlertService
from observability.mail_cost import MailCostTracker
from repositories.email_repository import EmailRepository
from repositories.extraction_repository import ExtractionRepository
from schemas.booking.triage import TriageOutcome, TriageResult
from services.classification import ClassificationService
from services.extraction import ExtractionService
from services.indexing import IndexingService
from services.ingestion import IngestionService
from services.response_generation import ResponseGenerationService
from services.retrieval import RetrievalService
from services.validation import ValidationService
from workflows.state import EmailWorkflowState


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
        self._mail_cost = mail_cost
        self._graph = self._build()
        self._checkpointer = MemorySaver()
        self._app = self._graph.compile(
            checkpointer=self._checkpointer,
            interrupt_before=["human_review"],
        )

    def _build(self) -> StateGraph:
        graph: StateGraph = StateGraph(EmailWorkflowState)
        graph.add_node("ingest", self._node_ingest)
        graph.add_node("classify", self._node_classify)
        graph.add_node("extract", self._node_extract)
        graph.add_node("validate", self._node_validate)
        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("draft_response", self._node_draft)
        graph.add_node("human_review", self._node_human_review)
        graph.add_node("finalize", self._node_finalize)

        graph.set_entry_point("ingest")
        graph.add_conditional_edges(
            "ingest",
            self._after_ingest,
            {"end": END, "classify": "classify"},
        )
        graph.add_edge("classify", "extract")
        graph.add_edge("extract", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_validate,
            {"end": END, "retrieve": "retrieve"},
        )
        graph.add_edge("retrieve", "draft_response")
        graph.add_edge("draft_response", "human_review")
        graph.add_edge("human_review", "finalize")
        graph.add_edge("finalize", END)
        return graph

    def run(
        self,
        email_input: Any,
        thread_id: str,
    ) -> dict[str, Any]:
        """Startet Workflow; stoppt vor human_review wenn nicht discarded."""
        config = {"configurable": {"thread_id": thread_id}}
        initial: EmailWorkflowState = {"email": email_input}
        result_dict: dict[str, Any] | None = None
        try:
            result_dict = dict(self._app.invoke(initial, config=config))
            return result_dict
        finally:
            self._finalize_mail_cost(email_input, result_dict)

    def resume_after_approval(
        self,
        thread_id: str,
        approved_body: str | None = None,
    ) -> dict[str, Any]:
        """Setzt Workflow nach Freigabe fort (gleiche thread_id)."""
        config = {"configurable": {"thread_id": thread_id}}
        result_dict: dict[str, Any] | None = None
        try:
            result_dict = dict(self._app.invoke(None, config=config))
            out = result_dict
            out["review"] = ReviewStatus(
                correlation_id=thread_id,
                status="approved",
                approved_body=approved_body,
            )
            return out
        finally:
            if self._mail_cost is not None:
                self._mail_cost.finalize(thread_id)

    def _finalize_mail_cost(
        self,
        email_input: Any,
        result: dict[str, Any] | None,
    ) -> None:
        """Aggregierte Kosten pro Mail – auch bei Spam/Abbruch vor Draft."""
        if self._mail_cost is None:
            return
        correlation_id = self._correlation_id(email_input, result)
        if correlation_id:
            self._mail_cost.finalize(correlation_id)

    def _correlation_id(
        self,
        email_input: Any,
        result: dict[str, Any] | None,
    ) -> str | None:
        if result is not None:
            email = result.get("email")
            if isinstance(email, StoredEmail):
                return email.correlation_id
        if isinstance(email_input, IncomingEmail | StoredEmail):
            return email_input.correlation_id
        return None

    def _after_ingest(self, state: EmailWorkflowState) -> Literal["end", "classify"]:
        if state.get("ingest_discarded"):
            return "end"
        return "classify"

    def _after_validate(self, state: EmailWorkflowState) -> Literal["end", "retrieve"]:
        errors = state.get("validation_errors") or []
        if errors:
            if self._alerts:
                email = state["email"]
                self._alerts.check_extraction_failure(
                    email.correlation_id,
                    "; ".join(errors),
                )
            return "end"
        return "retrieve"

    def _triage_from_email(self, email: StoredEmail) -> TriageResult:
        outcome = TriageOutcome.RELEVANT
        if email.triage_outcome:
            try:
                outcome = TriageOutcome(email.triage_outcome)
            except ValueError:
                outcome = TriageOutcome.UNKNOWN_DOMAIN
        return TriageResult(outcome=outcome, reason="ingested")

    def _node_ingest(self, state: EmailWorkflowState) -> EmailWorkflowState:
        raw = state.get("email")
        if isinstance(raw, IncomingEmail):
            result = self._ingestion.ingest(raw)
        elif isinstance(raw, StoredEmail):
            return {
                "email": raw,
                "ingest_duplicate": True,
                "ingest_discarded": False,
                "triage": self._triage_from_email(raw),
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
                self._triage_from_email(email)
                if not discarded
                else TriageResult(
                    outcome=TriageOutcome.SPAM_PHISHING,
                    reason=result.triage_reason or "spam",
                )
            ),
        }

    def _node_classify(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        intent = self._classification.classify(email)
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.CLASSIFIED,
        )
        return {"intent": intent}

    def _node_extract(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        intent = state.get("intent")
        extraction = self._extraction.extract(email, intent=intent)
        self._extraction_repo.save(
            email.correlation_id,
            email.message_id,
            extraction,
        )
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.EXTRACTED,
        )
        return {"extraction": extraction}

    def _node_validate(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        extraction = state["extraction"]
        result = self._validation.validate(extraction)
        if result.valid:
            self._email_repo.update_processing_state(
                email.message_id,
                ProcessingState.VALIDATED,
            )
            if self._indexing is not None:
                self._indexing.schedule_index(
                    email.correlation_id,
                    email.body_text,
                    extraction,
                )
        return {"validation_errors": result.errors}

    def _node_retrieve(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        extraction = state.get("extraction")
        hits = self._retrieval.retrieve(
            email,
            extraction,
            include_similar=True,
        )
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.RETRIEVED,
        )
        return {"retrieval": hits}

    def _node_draft(self, state: EmailWorkflowState) -> EmailWorkflowState:
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
        )
        return {
            "draft": draft,
            "grounding_flag": grounding_flag,
        }

    def _node_human_review(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        review = ReviewStatus(
            correlation_id=email.correlation_id,
            status="pending",
        )
        self._email_repo.update_processing_state(
            email.message_id,
            ProcessingState.PENDING_REVIEW,
        )
        return {"review": review}

    def _node_finalize(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        review = state.get("review")
        status = review.status if review else "approved"
        if status == "approved":
            proc = ProcessingState.APPROVED
        else:
            proc = ProcessingState.PENDING_REVIEW
        self._email_repo.update_processing_state(email.message_id, proc)
        return {
            "review": ReviewStatus(
                correlation_id=email.correlation_id,
                status=status,
                approved_body=review.approved_body if review else None,
            ),
        }

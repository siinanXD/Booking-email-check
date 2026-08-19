"""Dedizierter Graph-Zweig für mandantenspezifische Custom-Workflows.

Custom-Workflows (Orders, Support, …) teilen sich ingest/classify mit dem
Booking-Pfad, laufen danach aber komplett getrennt: Extraktion + Validierung
in einem Knoten, kein Retrieval, kein Draft, kein Human Review.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.ai.domain.booking.booking_relevance import relevance_fields
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.workflows.state import EmailWorkflowState
from backend.core.models.email import ProcessingState

if TYPE_CHECKING:
    from backend.ai.services.tenant_workflow_runtime import TenantWorkflowExecutor
    from backend.infrastructure.observability.alerts import AlertService
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.tenant_workflow_repository import (
        TenantWorkflowRepository,
    )


class TenantWorkflowMixin:
    """Extraktion + Validierung für Custom-Workflows in einem Knoten."""

    _email_repo: EmailRepository
    _extraction_repo: ExtractionRepository
    _alerts: AlertService | None
    _tenant_executor: TenantWorkflowExecutor | None
    _tenant_workflow_repo: TenantWorkflowRepository | None

    def tenant_process(self, state: EmailWorkflowState) -> EmailWorkflowState:
        email = state["email"]
        workflow_id = state.get("workflow_id") or ""
        workflow = (
            self._tenant_workflow_repo.get(email.account_id or "", workflow_id)
            if self._tenant_workflow_repo is not None
            else None
        )
        if workflow is None or self._tenant_executor is None:
            # Workflow zwischen classify und hier gelöscht/deaktiviert:
            # sauber beenden statt in den Booking-Pfad zu fallen.
            return {"validation_errors": ["tenant workflow unavailable"]}
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
            **relevance_fields(email, extraction),
        )
        errors = self._tenant_executor.validate_fields(workflow, custom)
        if errors:
            if self._alerts is not None:
                self._alerts.check_extraction_failure(
                    email.correlation_id,
                    "; ".join(errors),
                )
        else:
            self._email_repo.update_processing_state(
                email.message_id,
                ProcessingState.VALIDATED,
                account_id=email.account_id,
            )
        return {
            "extraction": extraction,
            "custom_extraction": custom,
            "validation_errors": errors,
        }

"""Tests für Workflow-Routing und Live-Pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.services.tenant_workflow_runtime import WorkflowRouter
from backend.core.models.email import IncomingEmail, StoredEmail
from backend.infrastructure.repositories.tenant_workflow_repository import (
    TenantWorkflowRecord,
    WorkflowMatchRules,
    WorkflowTestEmail,
)


def _stored(**kwargs: object) -> StoredEmail:
    defaults = {
        "message_id": "m1",
        "from_address": "shop@example.com",
        "subject": "Ihre Bestellung ORD-9912",
        "body_text": "Bestellnummer ORD-9912 Betrag 89 EUR",
        "received_at": datetime.now(UTC),
        "account_id": "acc-1",
        "correlation_id": "corr-1",
    }
    defaults.update(kwargs)
    return StoredEmail.model_validate(defaults)


def test_workflow_router_matches_keywords(mock_db: object) -> None:
    from backend.infrastructure.repositories.tenant_workflow_repository import (
        TenantWorkflowRepository,
    )

    repo = TenantWorkflowRepository(mock_db)
    repo.create(
        TenantWorkflowRecord(
            id="",
            account_id="acc-1",
            slug="purchase_confirmation",
            label="Kaufbestätigung",
            enabled=True,
            sandbox_only=False,
            extract_prompt="Extrahiere JSON {subject} {body}",
            match_rules=WorkflowMatchRules(subject_keywords=["bestellung"]),
            test_emails=[WorkflowTestEmail(subject="x", body="y")],
        )
    )
    router = WorkflowRouter(repo)
    matched = router.match("acc-1", _stored())
    assert matched is not None
    assert matched.workflow.slug == "purchase_confirmation"


def test_workflow_router_ignores_sandbox(mock_db: object) -> None:
    from backend.infrastructure.repositories.tenant_workflow_repository import (
        TenantWorkflowRepository,
    )

    repo = TenantWorkflowRepository(mock_db)
    repo.create(
        TenantWorkflowRecord(
            id="",
            account_id="acc-1",
            slug="sandbox_only",
            label="Sandbox",
            enabled=True,
            sandbox_only=True,
            extract_prompt="Extrahiere JSON {subject} {body}",
            match_rules=WorkflowMatchRules(subject_keywords=["bestellung"]),
        )
    )
    router = WorkflowRouter(repo)
    assert router.match("acc-1", _stored()) is None


def test_live_tenant_workflow_in_pipeline(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    mock_db,
) -> None:
    from backend.infrastructure.repositories.embedding_repository import (
        EmbeddingRepository,
    )
    from backend.infrastructure.repositories.tenant_workflow_repository import (
        TenantWorkflowRepository,
    )
    from tests.test_workflow import _build_workflow

    repo = TenantWorkflowRepository(mock_db)
    repo.create(
        TenantWorkflowRecord(
            id="",
            account_id="tenant-live",
            slug="purchase_confirmation",
            label="Kaufbestätigung",
            enabled=True,
            sandbox_only=False,
            classify_prompt="Klassifiziere. Slug: match oder other. {subject} {body}",
            extract_prompt=(
                "Extrahiere strukturierte Metadaten als JSON. {subject} {body}"
            ),
            required_fields=[],
            match_rules=WorkflowMatchRules(subject_keywords=["bestellung"]),
            test_emails=[
                WorkflowTestEmail(
                    subject="Bestellung ORD-9912",
                    body="Bestellnummer ORD-9912",
                )
            ],
        )
    )

    wf = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        EmbeddingRepository(mock_db),
        tenant_workflow_repo=repo,
    )
    payload = IncomingEmail(
        message_id="live-wf-1",
        from_address="shop@notifications.booking.com",
        subject="Ihre Bestellung Buchung ORD-9912",
        body_text="Bestellnummer ORD-9912 vom ExampleShop.",
        received_at=datetime.now(UTC),
        account_id="tenant-live",
        correlation_id="live-corr-1",
    )
    result = wf.run(payload, thread_id="live-corr-1")
    assert result.get("workflow_id")
    assert result.get("custom_extraction")
    custom = extraction_repo.get_custom_fields(
        "live-corr-1",
        account_id="tenant-live",
    )
    assert custom is not None
    assert "draft" not in result
